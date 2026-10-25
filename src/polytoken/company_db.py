"""Bootstrap/writes for the fictional source DB. Investigation reads use Zetaris."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from indictax.corpus import load_corpus

from .config import Settings
from .logs import JsonlLogger
from .prices import load_prices

# Source checkout, or a non-editable installation invoked from the cloned repo.
from .paths import ROOT
if not (ROOT / 'data/demo').is_dir():
    ROOT = Path.cwd()
COMPANIES = ('samudra', 'swara', 'raitu', 'paisa')
CONFIG_FIELDS = ('company', 'language', 'system_prompt_native', 'system_prompt_en', 'model_in_use', 'monthly_chats', 'latency_target_s', 'review_status', 'role', 'channel', 'current_model', 'dataset_version')
CHAT_FIELDS = ('chat_id', 'turn', 'role', 'text_native', 'text_en', 'lang', 'review_status')
REFERENCE_FIELDS = ('id', 'lang_variant', 'domain', 'kind', 'text', 'review')
PRICE_FIELDS = ('model', 'provider', 'tokenizer_spec', 'input_per_mtok_usd', 'output_per_mtok_usd', 'source_url', 'fetched_at', 'verified')


def connect(settings: Settings):
    settings.require_company_db()
    return psycopg.connect(host='127.0.0.1', port=55432, dbname='company_systems',
                           user=settings.company_db_user, password=settings.company_db_password,
                           connect_timeout=10)


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def load_demo(directory=ROOT / 'data/demo'):
    directory = Path(directory)
    configs = jsonl(directory / 'bot_config.jsonl')
    if sorted(row['company'] for row in configs) != sorted(COMPANIES):
        raise ValueError('Expected one bot configuration for each demo company')
    chats = {}
    for config in configs:
        company = config['company']
        if config['review_status'] != 'pending':
            raise ValueError('Generated demo configuration must remain pending')
        chats[company] = jsonl(directory / f'{company}_chats.jsonl')
        by_chat = defaultdict(list)
        for row in chats[company]:
            if row['review_status'] != 'pending' or row['lang'] != config['language']:
                raise ValueError('Demo language/review status does not match its configuration')
            if not row['text_native'].strip() or not row['text_en'].strip():
                raise ValueError('Every turn needs a native and English pair')
            by_chat[row['chat_id']].append(row)
        if len(by_chat) != 40:
            raise ValueError('Expected exactly 40 fictional chats per company')
        for rows in by_chat.values():
            if not 3 <= len(rows) <= 6 or [r['turn'] for r in rows] != list(range(1, len(rows)+1)):
                raise ValueError('Chat turns must be consecutive and number 3 through 6')
            if any(r['role'] != ('user' if r['turn'] % 2 else 'assistant') for r in rows):
                raise ValueError('Chat roles must alternate, starting with user')
    for config in configs:
        if config['system_prompt_native'] != config['system_prompt_en'] or not config['system_prompt_en'].isascii():
            raise ValueError('All instructions must be English and identical in both paired columns')
        if config['channel'] not in ('chat', 'voice') or not config['role']:
            raise ValueError('Company needs a role and channel')
    return configs, chats


def load_reference(path):
    rows = []
    for item in load_corpus(path):
        for variant, text in item.variants.items():
            rows.append(dict(id=item.id, lang_variant=variant, domain=item.domain, kind=item.kind,
                             text=text, review=json.dumps(item.review, ensure_ascii=False, sort_keys=True)))
    return rows


def create_schema(connection):
    for statement in (ROOT / 'sql/company_schema.sql').read_text().split(';'):
        if statement.strip():
            connection.execute(statement)


def upsert(connection, table, fields, keys, rows):
    # All identifiers come from constants in this module, never untrusted input.
    placeholders = ', '.join('%s' for _ in fields)
    updates = ', '.join(f'{field}=excluded.{field}' for field in fields if field not in keys)
    query = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders}) ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {updates}"
    with connection.cursor() as cursor:
        cursor.executemany(query, [tuple(row[field] for field in fields) for row in rows])


def seed_records(connection, configs, chats, references, prices):
    for company in COMPANIES:
        # Replace the current fictional dataset transactionally; earlier files and measurements remain archived.
        connection.execute(f'DELETE FROM {company}.chats')
        upsert(connection, f'{company}.bot_config', CONFIG_FIELDS, ('company',),
               [r for r in configs if r['company'] == company])
        upsert(connection, f'{company}.chats', CHAT_FIELDS, ('chat_id', 'turn'), chats[company])
    upsert(connection, 'reference.sentences', REFERENCE_FIELDS, ('id', 'lang_variant'), references)
    upsert(connection, 'reference.prices', PRICE_FIELDS, ('provider', 'model'), prices)


def seed_company_db(settings, logger=None, reference_path=ROOT / 'data/reference/seed_v0_corrected.jsonl'):
    logger = logger or JsonlLogger(secrets=settings.secrets)
    started = datetime.now(timezone.utc)
    configs, chats = load_demo()
    reference_path = Path(reference_path)
    references = load_reference(reference_path)
    prices = load_prices(ROOT / 'data/reference/prices.json')
    try:
        with connect(settings) as connection:
            create_schema(connection)
            seed_records(connection, configs, chats, references, prices)
            counts = {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                      for table in (*(f'{c}.{t}' for c in COMPANIES for t in ('bot_config', 'chats')), 'reference.sentences', 'reference.prices')}
    except Exception as exc:
        logger.write('data_setup', 'seed', ok=False, error_class=type(exc).__name__)
        raise
    logger.write('data_setup', 'seed', ok=True, counts=counts,
                 source=str(reference_path), source_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                 query='idempotent parameterized upserts into company_systems',
                 time_window={'start':started.isoformat(), 'end':datetime.now(timezone.utc).isoformat()},
                 fetched_at=datetime.now(timezone.utc).isoformat())
    return counts
