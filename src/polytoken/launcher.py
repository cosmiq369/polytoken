"""Validated local imports. Only generated identifiers reach SQL identifiers."""
import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .company_db import COMPANIES
from .paths import ROOT
from .prices import load_prices

MAX_BYTES = 1_048_576


def validate_sample_file(path, language):
    """Use exactly the launcher's parser; retain neither paths nor sample text in output."""
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        raise ValueError('Cannot read sample file') from None
    if len(raw) > MAX_BYTES:
        raise ValueError('Sample exceeds the one MiB limit')
    try:
        content = raw.decode('utf-8')
    except UnicodeError:
        raise ValueError('Sample must be UTF-8') from None
    rows = parse_sample(Path(path).name, content, language)
    return dict(rows=len(rows), chats=len({r['chat_id'] for r in rows}), review_status='pending')


def valid_company(value):
    return value in COMPANIES or bool(re.fullmatch(r'upload_[a-f0-9]{32}', value))


def priced_models():
    return sorted({p['model'] for p in load_prices(ROOT / 'data/reference/prices.json')
                   if p['verified'] and p['input_per_mtok_usd'] is not None and p['output_per_mtok_usd'] is not None})


class Launch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=100)
    industry: str = Field(min_length=1, max_length=100)
    channel: Literal['chat', 'voice']
    language: Literal['te', 'hi']
    monthly_chats: int = Field(gt=0, le=1_000_000_000, strict=True)
    candidate_models: list[str] = Field(min_length=1, max_length=20)
    currency: Literal['USD', 'INR'] = 'INR'
    sample: Literal['samudra', 'swara', 'raitu', 'paisa'] | None = None
    filename: str | None = Field(default=None, max_length=150)
    content: str | None = Field(default=None, max_length=MAX_BYTES)
    system_prompt: str = Field(default='Help the customer using the supplied conversation context.', min_length=1, max_length=4000)
    latency_target_s: float = Field(default=2., gt=0, le=300, allow_inf_nan=False)

    @model_validator(mode='after')
    def validate_input(self):
        if not self.name.strip() or not self.industry.strip() or not self.system_prompt.strip():
            raise ValueError('Name, industry and system prompt must not be blank')
        if len(set(self.candidate_models)) != len(self.candidate_models) or not set(self.candidate_models) <= set(priced_models()):
            raise ValueError('Choose distinct models from the priced list')
        if self.sample:
            if self.content is not None or self.filename is not None:
                raise ValueError('Choose a bundled sample or upload, not both')
            expected = 'te' if self.sample in ('samudra', 'raitu') else 'hi'
            if self.language != expected:
                raise ValueError('Language does not match the selected bundled sample')
        else:
            if self.content is None or not self.filename:
                raise ValueError('Choose a bundled sample or upload JSONL/CSV')
            parse_sample(self.filename, self.content, self.language)
        return self


def parse_sample(filename, content, language):
    if len(content.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Sample exceeds the one MiB limit')
    try:
        if filename.lower().endswith('.jsonl'):
            rows = []
            for number, line in enumerate(content.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    raise ValueError(f'Invalid JSONL at line {number}') from None
        elif filename.lower().endswith('.csv'):
            reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
                raise ValueError('Duplicate CSV columns')
            rows = list(reader)
        else:
            raise ValueError('Use a .jsonl or .csv file')
    except csv.Error:
        raise ValueError('Invalid CSV structure; use the downloadable template') from None
    if not 2 <= len(rows) <= 500:
        raise ValueError('Supply between two and five hundred paired turns')
    required = {'chat_id', 'turn', 'role', 'text_native', 'text_en', 'lang'}
    grouped = defaultdict(list)
    cleaned = []
    for number, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict) or not required <= row.keys() or set(row) - required - {'review_status'}:
                raise ValueError('Each row needs chat_id, turn, role, text_native, text_en and lang only')
            if not isinstance(row['chat_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', row['chat_id']):
                raise ValueError('Chat identifiers must use letters, digits, hyphens or underscores')
            turn = row['turn']
            if isinstance(turn, str) and turn.isdigit(): turn = int(turn)
            if type(turn) is not int or not 1 <= turn <= 100:
                raise ValueError('Turn must be a positive integer up to one hundred')
            if row['lang'] != language or row['role'] not in ('user', 'assistant'):
                raise ValueError('Language must match the form and role must be user or assistant')
            for field in ('text_native', 'text_en'):
                if not isinstance(row[field], str) or not row[field].strip() or len(row[field]) > 4000:
                    raise ValueError('Paired texts must be nonempty and at most four thousand characters')
            wrong = r'[\u0900-\u097f]' if language == 'te' else r'[\u0c00-\u0c7f]'
            if re.search(wrong, row['text_native']) or re.search(r'[\u0900-\u097f\u0c00-\u0c7f]', row['text_en']):
                raise ValueError('Native script conflicts with selected language or English baseline')
            item = {k: row[k] for k in required}
            item.update(turn=turn, review_status='pending')
            cleaned.append(item); grouped[row['chat_id']].append(item)
        except ValueError as exc:
            raise ValueError(f'Row {number}: {exc}') from None
    for turns in grouped.values():
        turns.sort(key=lambda r:r['turn'])
        if [r['turn'] for r in turns] != list(range(1,len(turns)+1)) or len(turns)<2:
            raise ValueError('Each chat needs consecutive turns starting at one, with at least one reply')
        if any(r['role'] != ('user' if i%2 == 0 else 'assistant') for i,r in enumerate(turns)):
            raise ValueError('Roles must alternate, starting with user')
    return sorted(cleaned,key=lambda r:(r['chat_id'],r['turn']))


def ingest(launch, settings, client, logger, *, run_id):
    """Write an isolated source, register its projections, measure via Zetaris.

    The four reviewed fixtures are never replaced. Registration/measurement failure
    leaves an auditable failed run, never fabricated or partial paired counts.
    """
    from .company_db import connect, upsert, CHAT_FIELDS, CONFIG_FIELDS, jsonl
    from .measure import read_inputs, measure_batch, write_batch
    from .tokens import local_tokenizer_files, _tokenizer, count, fragment_rate
    company = 'upload_' + uuid4().hex
    rows = jsonl(ROOT / f'data/demo/{launch.sample}_chats.jsonl') if launch.sample else parse_sample(launch.filename, launch.content, launch.language)
    prices = [p for p in load_prices(ROOT/'data/reference/prices.json') if p['model'] in launch.candidate_models and p['verified']]
    specs = sorted({p['tokenizer_spec'] for p in prices})
    config = dict(company=company, language=launch.language, system_prompt_native=launch.system_prompt,
                  system_prompt_en=launch.system_prompt, model_in_use=prices[0]['tokenizer_spec'],
                  monthly_chats=launch.monthly_chats, latency_target_s=launch.latency_target_s,
                  review_status='pending', role=launch.industry, channel=launch.channel,
                  current_model=prices[0]['model'], dataset_version=company,
                  display_name=launch.name, currency=launch.currency,
                  candidate_models=json.dumps(launch.candidate_models))
    # company is generated above; no user-controlled SQL identifiers or literals.
    with connect(settings) as db:
        db.execute(f'CREATE SCHEMA {company}')
        db.execute(f'CREATE TABLE {company}.bot_config (LIKE samudra.bot_config INCLUDING ALL)')
        for field in ('display_name', 'currency', 'candidate_models'):
            db.execute(f'ALTER TABLE {company}.bot_config ADD COLUMN {field} TEXT')
        db.execute(f'CREATE TABLE {company}.chats (LIKE samudra.chats INCLUDING ALL)')
        upsert(db, f'{company}.bot_config', (*CONFIG_FIELDS,'display_name','currency','candidate_models'), ('company',), [config])
        upsert(db, f'{company}.chats', CHAT_FIELDS, ('chat_id','turn'), rows)
        for table in ('bot_config','chats'):
            db.execute(f'CREATE VIEW public.{company}__{table} AS SELECT * FROM {company}.{table}')
    client.execute(f'REGISTER DATASOURCE TABLES ("{company}__bot_config", "{company}__chats") FROM company_systems')
    items, provenance = read_inputs(client, company)
    files = local_tokenizer_files()
    completed = []
    for spec in specs:
        def local_spec(value):
            if not files.get(value): raise ValueError('Tokenizer unavailable locally; install its cache during setup')
            return 'file:' + files[value]
        measured, batch, elapsed = measure_batch(items, spec, run_id, provenance,
            load=lambda s:_tokenizer(local_spec(s)), count=lambda s,t:count(local_spec(s),t),
            fragment=lambda s,t:fragment_rate(local_spec(s),t), redact=logger.redact)
        write_batch(settings, measured, batch)
        logger.write('measurements', 'batch', **batch, ok=batch['status']=='completed', elapsed_s=elapsed)
        if batch['status']=='completed': completed.append(spec)
    if config['model_in_use'] not in completed:
        raise RuntimeError('Selected baseline tokenizer unavailable; cache tokenizers before retrying')
    logger.write('launcher','source_ingested',company=company,display_name=launch.name,
                 source='Local uploaded sample' if not launch.sample else 'Bundled synthetic sample',
                 query=provenance['source_query'],fetched_at=provenance['fetched_at'],
                 time_window={'start':provenance['time_window_start'],'end':provenance['time_window_end']},ok=True)
    return company
