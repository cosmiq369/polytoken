"""Strict reference loaders. Catalogue entries become usable only after live discovery."""
import json
import math
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2] / 'data/reference'
if not (ROOT / 'prices.json').is_file():
    ROOT = Path.cwd() / 'data/reference'


def _read(name, path):
    row = json.loads(Path(path or ROOT / name).read_text())
    if not isinstance(row, dict) or row.get('verified') is False:
        raise ValueError('Unverified reference data')
    if urlsplit(row.get('source_url', '')).scheme != 'https':
        raise ValueError('Reference requires an HTTPS source')
    if datetime.fromisoformat(row['fetched_at'].replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Reference requires a timezone')
    return row


def load_fx(path=None):
    # Keep the agent's historical INR contract while display currencies grow by row.
    data = json.loads(Path(path or ROOT / 'fx.json').read_text())
    if isinstance(data, dict) and 'rates' in data:
        from .currencies import load_currencies
        rates = load_currencies(path or ROOT / 'fx.json')['rates']
        found = next((r for r in rates if r['currency'] == 'INR'), None)
        if found is None:
            raise ValueError('Verified USD/INR rate required by historical accounting')
        row = {k: v for k, v in found.items() if k not in ('currency', 'per_usd')}
        row.update(pair='USD/INR', inr_per_usd=found['per_usd'])
    else:
        row = _read('fx.json', path)
    value = row.get('inr_per_usd')
    if (row.get('verified') is not True or row.get('pair') != 'USD/INR'
            or type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
        raise ValueError('Verified positive USD/INR rate required')
    if datetime.fromisoformat(row['as_of']).tzinfo is None:
        raise ValueError('FX as_of requires a timezone')
    return row


def load_hosted(path=None):
    row = _read('nvidia_hosted.json', path)
    families = row.get('families')
    if not isinstance(families, dict) or not families:
        raise ValueError('Hosted families required')
    for family, models in families.items():
        if not isinstance(family, str) or not isinstance(models, list) or any(
                not isinstance(m, str) or not m or '/' not in m for m in models):
            raise ValueError('Invalid hosted family')
    # The staged catalogue has no verified field. It is an allowlist only;
    # intersection with a successful live /models response is mandatory.
    return row
