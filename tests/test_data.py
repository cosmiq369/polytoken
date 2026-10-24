import json
import sqlite3
from contextlib import contextmanager
from decimal import Decimal

import pytest

from polytoken.company_db import (ROOT, load_demo, load_reference, seed_records)
from polytoken.prices import PriceUnavailable, cost_usd, load_prices


def test_demo_and_reference_review_preserved():
    configs, chats = load_demo()
    assert all(r['review_status'] == 'pending' for r in configs)
    assert [len(chats[c]) for c in ('samudra', 'swara')] == [223, 223]
    path = ROOT.parent / 'solve-it/data/prompts/seed_v0_corrected.jsonl'
    originals = {r['id']: r for r in map(json.loads, path.read_text().splitlines())}
    references = load_reference(path)
    assert len(references) == 118
    for row in references:
        assert json.loads(row['review']) == originals[row['id']].get('review')


class SQLiteSeedConnection:
    """Execute production upserts against SQL constraints, with placeholder translation."""
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        for schema in ('samudra', 'swara', 'reference', 'measurements'):
            self.db.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
        for statement in (ROOT / 'sql/company_schema.sql').read_text().split(';'):
            if statement.strip().startswith('CREATE TABLE'):
                self.db.execute(statement)

    @contextmanager
    def cursor(self):
        yield self

    def executemany(self, sql, values):
        self.db.executemany(sql.replace('%s', '?'), values)


def test_seeder_idempotence_uses_real_sql_upserts():
    configs, chats = load_demo()
    refs = load_reference(ROOT.parent / 'solve-it/data/prompts/seed_v0_corrected.jsonl')
    connection = SQLiteSeedConnection()
    tables = ('samudra.bot_config', 'samudra.chats', 'swara.bot_config', 'swara.chats', 'reference.sentences', 'reference.prices')
    def counts():
        return [connection.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in tables]
    seed_records(connection, configs, chats, refs, [])
    first = counts()
    seed_records(connection, configs, chats, refs, [])
    assert counts() == first == [1, 223, 1, 223, 118, 0]


@pytest.fixture
def price():
    # Explicit test-only synthetic rates, never loaded into the demo DB.
    return dict(model='fixture', provider='fixture', tokenizer_spec='fixture',
                input_per_mtok_usd=2, output_per_mtok_usd=8,
                source_url='https://example.test/fixture', fetched_at='2026-10-24T00:00:00Z', verified=True)


def test_empty_prices_refuse_money():
    assert load_prices(ROOT / 'data/reference/prices.json') == []
    with pytest.raises(PriceUnavailable, match='verified price'):
        cost_usd(None, 10, 20)


def test_price_exact_decimal_and_fail_closed(price):
    assert cost_usd(price, 1000, 250) == Decimal('0.004')
    with pytest.raises(PriceUnavailable, match='verified price'):
        cost_usd({**price, 'verified': False}, 1000, 250)
    for name in ('input_per_mtok_usd', 'output_per_mtok_usd'):
        with pytest.raises(PriceUnavailable, match='both required'):
            cost_usd({**price, name: None}, 1000, 250)


@pytest.mark.parametrize('bad', [-1, float('nan'), float('inf'), True, '1.0'])
def test_invalid_prices_rejected(price, bad):
    with pytest.raises(ValueError):
        cost_usd({**price, 'input_per_mtok_usd': bad}, 1, 1)
