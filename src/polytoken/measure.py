"""Token measurements from Zetaris inputs; direct DB access is write-only here."""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import tokens
from .company_db import ROOT, COMPANIES, connect, upsert
from .logs import JsonlLogger
from .zetaris import ZetarisClient

COUNT_FIELDS = ('company', 'chat_id', 'turn', 'part', 'tokenizer_spec', 'lang_variant',
                'tokens', 'fragment_rate', 'run_id', 'measured_at', 'source', 'source_query',
                'fetched_at', 'time_window_start', 'time_window_end')
BATCH_FIELDS = ('run_id', 'company', 'tokenizer_spec', 'status', 'reason', 'rows_written',
                'started_at', 'finished_at', 'source_query', 'fetched_at')


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def tokenizer_specs(path=ROOT / 'configs/tokenizers.yaml'):
    specs = [row['spec'] for row in yaml.safe_load(Path(path).read_text())['tokenizers']]
    if not specs or len(specs) != len(set(specs)) or any(not isinstance(s, str) or not s for s in specs):
        raise ValueError('Expected distinct nonempty tokenizer specs')
    return specs


def read_inputs(client, company):
    if company not in COMPANIES:
        raise ValueError('Unknown company')
    queries = [f'SELECT * FROM company_systems.{company}__bot_config',
               f'SELECT * FROM company_systems.{company}__chats ORDER BY chat_id, turn']
    start = utcnow()
    configs = client.query(queries[0], page_limit=10000)
    chats = client.query(queries[1], page_limit=10000)
    fetched = utcnow()
    if len(configs) != 1 or not chats:
        raise ValueError('A company needs one configuration and nonempty chats')
    config = configs[0]
    items = [dict(company=company, chat_id='__system__', turn=0, part='system_prompt',
                  native=config['system_prompt_native'], en=config['system_prompt_en'],
                  lang=config['language'])]
    seen = set()
    for row in chats:
        key = (row['chat_id'], int(row['turn']))
        if key in seen or row['role'] not in ('user', 'assistant') or row['lang'] != config['language']:
            raise ValueError('Invalid or duplicate chat input')
        seen.add(key)
        items.append(dict(company=company, chat_id=key[0], turn=key[1], part=row['role'],
                          native=row['text_native'], en=row['text_en'], lang=row['lang']))
    if any(not isinstance(item[v], str) or not item[v].strip() for item in items for v in ('native', 'en')):
        raise ValueError('Every measurement needs a nonempty native/English pair')
    return items, dict(source_query=';\n'.join(queries), fetched_at=fetched,
                       time_window_start=start, time_window_end=fetched)


def measure_batch(items, spec, run_id, provenance, *, load=tokens._tokenizer,
                  count=tokens.count, fragment=tokens.fragment_rate, redact=lambda value: value):
    started, clock_start = utcnow(), time.monotonic()
    batch = dict(run_id=run_id, company=items[0]['company'], tokenizer_spec=spec,
                 status='completed', reason=None, rows_written=0, started_at=started,
                 source_query=provenance['source_query'], fetched_at=provenance['fetched_at'])
    rows = []
    try:
        load(spec)
    except Exception as exc:
        batch.update(status='skipped', reason=redact(f'{type(exc).__name__}: {exc}')[:600])
    if batch['status'] == 'completed':
        try:
            for item in items:
                for variant, language in (('native', item['lang']), ('en', 'en')):
                    value = count(spec, item[variant])
                    rate = fragment(spec, item[variant])
                    if type(value) is not int or value <= 0 or not math.isfinite(rate) or not 0 <= rate <= 1:
                        raise ValueError('Invalid measurement for nonempty text')
                    rows.append(dict(company=item['company'], chat_id=item['chat_id'], turn=item['turn'],
                                     part=item['part'], tokenizer_spec=spec, lang_variant=language,
                                     tokens=value, fragment_rate=rate, run_id=run_id, measured_at=utcnow(),
                                     source='Zetaris SQL + indictax tokenizer', **provenance))
        except Exception as exc:
            # A partial batch cannot support a paired comparison.
            rows = []
            batch.update(status='failed', reason=redact(f'{type(exc).__name__}: {exc}')[:600])
    batch.update(rows_written=len(rows), finished_at=utcnow())
    return rows, batch, time.monotonic()-clock_start


def write_batch(settings, rows, batch):
    with connect(settings) as connection:
        if rows:
            upsert(connection, 'measurements.token_counts', COUNT_FIELDS,
                   ('company', 'chat_id', 'turn', 'part', 'tokenizer_spec', 'lang_variant', 'run_id'), rows)
        upsert(connection, 'measurements.batches', BATCH_FIELDS,
               ('run_id', 'company', 'tokenizer_spec'), [batch])


def measure(settings, company='all', logger=None):
    logger = logger or JsonlLogger(secrets=settings.secrets)
    companies = COMPANIES if company == 'all' else (company,)
    settings.require_company_db()
    batches = []
    with ZetarisClient(settings, logger=logger) as client:
        inputs = {name: read_inputs(client, name) for name in companies}
    for spec in tokenizer_specs():
        for name in companies:
            items, provenance = inputs[name]
            rows, batch, elapsed = measure_batch(items, spec, logger.run_id, provenance, redact=logger.redact)
            try:
                write_batch(settings, rows, batch)
            except Exception as exc:
                logger.write('measurements', 'batch', **{**batch, 'status':'failed', 'rows_written':0},
                             ok=False, error_class=type(exc).__name__, elapsed_s=elapsed)
                raise
            logger.write('measurements', 'batch', **batch, ok=batch['status']=='completed',
                         elapsed_s=elapsed, input_items=len(items), source='Zetaris SQL + indictax',
                         time_window={'start':provenance['time_window_start'], 'end':provenance['time_window_end']})
            print(f"{name} | {spec} | {batch['status']} | {len(rows)} rows", flush=True)
            if batch['reason']:
                print('  ' + batch['reason'], flush=True)
            batches.append(batch)
    return batches
