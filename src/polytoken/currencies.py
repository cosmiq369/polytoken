"""Sourced display currencies. USD is a denomination, not an invented FX quote."""
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


def load_currencies(path=None):
    data = json.loads(Path(path or ROOT / 'data/reference/fx.json').read_text())
    if not isinstance(data, dict) or data.get('base') != 'USD' or not isinstance(data.get('rates'), list):
        raise ValueError('FX requires base USD and a rates list')
    rows, seen = [], {'USD'}
    for row in data['rates']:
        code = row.get('currency')
        if not isinstance(code, str) or not re.fullmatch('[A-Z]{3}', code) or code in seen:
            raise ValueError('Distinct non-USD ISO currency codes required')
        seen.add(code)
        value = row.get('per_usd')
        if type(value) not in (int, float) or not Decimal(str(value)).is_finite() or value <= 0:
            raise ValueError('FX rate must be positive and finite')
        if row.get('verified') is not True:
            raise ValueError('Unverified FX row refused')
        if not row.get('source') or urlsplit(row.get('source_url', '')).scheme != 'https':
            raise ValueError('FX rate requires a source and HTTPS source URL')
        for key in ('as_of', 'fetched_at'):
            if datetime.fromisoformat(row[key].replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('FX dates require timezones')
        rows.append(dict(row))
    return {'base': 'USD', 'rates': [dict(currency='USD', per_usd=1, verified=True,
             source='Provider price denomination; no exchange conversion', source_url=None,
             as_of=None, fetched_at=None), *rows]}
