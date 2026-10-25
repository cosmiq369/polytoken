"""Offline-first installation checks; network probes require --live."""
import importlib.metadata
import json
import shutil
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from dotenv import dotenv_values

from .config import load_settings
from .logs import JsonlLogger
from .paths import ROOT
from .prices import load_prices

INDICTAX_PIN = '0f61ec90ae49082d0fef7a21774e746fe17ed1cf'
METERLESS_PIN = '1742dec56a66e58eef9dda2d2b865823758ca8cd'


def run_doctor(env_file='.env', *, live=False, port=8000, state_dir='.cache/state'):
    logger = JsonlLogger(env_file=env_file)
    checks = []
    def record(name, status, detail, fix=''):
        row = dict(check=name,status=status,detail=detail,fix=fix,ok=status=='PASS')
        checks.append(row); logger.write('doctor','check',**row)
        print(f'  {status}  {name}: {detail}' + (f' Fix: {fix}' if fix else ''))
    def probe(name, fn, fix):
        try: record(name,'PASS',fn())
        except Exception as exc: record(name,'FAIL',type(exc).__name__,fix)
    print('PolyToken doctor — ' + ('live probes enabled' if live else 'offline installation checks'))
    record('Python', 'PASS' if sys.version_info >= (3,10) else 'FAIL', '.'.join(map(str,sys.version_info[:3])),
           '' if sys.version_info >= (3,10) else 'Install Python >=3.10 and recreate .venv')
    def pin():
        d=importlib.metadata.distribution('indictax')
        source=json.loads(d.read_text('direct_url.json') or '{}')
        if source.get('vcs_info',{}).get('commit_id') != INDICTAX_PIN or source.get('url') != 'https://github.com/cosmiq369/indic-inference-tax':
            raise ValueError('Pinned installation required')
        return 'Installed Git commit matches pyproject.toml'
    probe('Pinned indictax',pin,"Install '.[dev]' from the clone; remove an editable harness override for release validation")
    def meterless():
        from .meterless.world_model import WorldModel
        from .meterless.hmem import HMem
        from .meterless.markovian import Markovian
        if METERLESS_PIN not in (ROOT/'docs/METERLESS.md').read_text(): raise ValueError('Missing architecture attribution')
        return 'Local engines import; reference architecture commit matches attribution'
    probe('Meterless',meterless,'Restore the tracked engines and docs/METERLESS.md; run pytest tests/meterless')
    def sqlite():
        folder=Path(state_dir);folder.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(dir=folder) as temporary:
            with sqlite3.connect(str(Path(temporary)/'probe.sqlite')) as db:
                db.execute('CREATE TABLE probe (ok INTEGER)');db.execute('INSERT INTO probe VALUES (1)')
                if db.execute('SELECT ok FROM probe').fetchone() != (1,):raise RuntimeError('SQLite probe failed')
        return 'State directory supports SQLite writes'
    probe('SQLite',sqlite,'Make the state directory writable by your user')
    def free_port():
        with socket.socket() as sock:sock.bind(('127.0.0.1',port))
        return f'Loopback port {port} is available'
    probe('App port',free_port,'Stop the existing app or use matching --port values for doctor and serve')
    free=shutil.disk_usage(Path.cwd()).free
    record('Disk space','PASS' if free >= 100*1024*1024 else 'WARN','At least one hundred MiB free' if free >=100*1024*1024 else 'Low free disk space',
           'Allow additional space for tokenizer caches and logs' if free <100*1024*1024 else '')
    def freshness():
        rows=load_prices(ROOT/'data/reference/prices.json')
        ages=[(datetime.now(timezone.utc)-datetime.fromisoformat(r['fetched_at'].replace('Z','+00:00'))).total_seconds()/86400 for r in rows if r['verified']]
        if not ages or min(ages)<0 or max(ages)>30:raise ValueError('Price source outside freshness policy')
        return 'Verified quotes are within the documented thirty-day freshness window'
    probe('Price source',freshness,'Reverify provider sources and update dated price references; never fabricate rates')
    import os
    values={**dotenv_values(env_file,interpolate=False),**os.environ}
    present=bool(values.get('NVIDIA_API_KEY'))
    record('NVIDIA key','PASS' if present else ('FAIL' if live else 'WARN'),'Present; value hidden' if present else 'Not configured',
           '' if present else 'Enter the key locally in .env for live mode; demo needs no key')
    if not live:
        record('Zetaris and NVIDIA serving','WARN','Not probed in offline mode','Run polytoken doctor --live after setup')
    else:
        try:settings=load_settings(env_file);logger.add_secrets(*settings.secrets)
        except Exception as exc:
            record('Live configuration','FAIL',type(exc).__name__,'Fill required variable names from .env.example locally')
        else:
            from .cli import check_zetaris, check_nvidia
            from .zetaris import ZetarisClient
            def port_probe():
                parsed=urlsplit(settings.zetaris_url)
                with socket.create_connection((parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80)),timeout=5):pass
                return 'Configured Zetaris TCP port is reachable'
            probe('Zetaris port',port_probe,'Start Zetaris or check the configured URL and SSH tunnel')
            probe('Zetaris SQL',lambda:check_zetaris(settings,logger),'Run the sponsor verify.sh; check local credentials and organisation access')
            def tables():
                names=['reference__sentences','measurements__latest_token_counts',*(f'{c}__{t}' for c in ('samudra','swara','raitu','paisa') for t in ('bot_config','chats'))]
                with ZetarisClient(settings,logger=logger) as client:
                    for name in names:
                        rows=client.query(f'SELECT COUNT(*) AS n FROM company_systems.{name}')
                        if not rows or int(rows[0]['n'])<=0:raise ValueError('Required source is empty')
                    prices=client.query('SELECT * FROM polytoken_reference.prices')
                    if not prices:raise ValueError('Price source is empty')
                    # A stale or altered live quote must not pass just because its table exists.
                    expected=load_prices(ROOT/'data/reference/prices.json')
                    from decimal import Decimal
                    for p in expected:
                        if not any(all((Decimal(str(r[k]))==Decimal(str(v)) if k.endswith('_usd') and v is not None else str(r.get(k)).lower()==str(v).lower()) for k,v in p.items()) for r in prices):
                            raise ValueError('Live prices differ from checked references')
                return 'Required views are populated; live prices match checked references'
            probe('Zetaris views and prices',tables,'Seed the source DB, register projections, keep reference server running and measure the bundled companies')
            probe('NVIDIA serving',lambda:check_nvidia(settings,logger),'Check AGENT_MODEL, NVIDIA_BASE_URL and access; inspect redacted logs')
    failed=sum(r['status']=='FAIL' for r in checks)
    print(f"{len(checks)} checks; {failed} failed; {sum(r['status']=='WARN' for r in checks)} warnings.")
    return int(bool(failed))
