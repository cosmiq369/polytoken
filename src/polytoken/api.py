"""Local FastAPI service with replayable, ordered SSE and a single run worker."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import asyncio
import json
import re
from pathlib import Path
import threading
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from .agent.runtime import investigate
from .logs import JsonlLogger
from .meterless.world_model import WorldModel
from .reference_server import ensure_reference_server, ensure_reference_table
from .tools import now


class InvestigationRequest(BaseModel):
    company: str
    question: str = ''
    monthly_chats: int | None = Field(default=None, gt=0)
    latency_target_s: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class Manager:
    def __init__(self, run=investigate):
        self.run = run
        self.runs = {}
        self.lock = threading.Lock()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='investigation')

    def start(self, payload):
        identifier = uuid4().hex
        state = {'events': [], 'report': None, 'finished': False}
        with self.lock:
            self.runs[identifier] = state
        def emit(row):
            with self.lock:
                state['events'].append(row)
        def work():
            try:
                def publish(report):
                    with self.lock:
                        state['report'] = report
                import inspect
                extra = {'report_sink': publish} if 'report_sink' in inspect.signature(self.run).parameters else {}
                report, _ = self.run(**payload, run_id=identifier, event_sink=emit, **extra)
                state['report'] = report
            except Exception as exc:
                state['report'] = {'id': identifier, 'status': 'partial', 'partial_reason': 'startup failed: ' + type(exc).__name__,
                                   'claims': [], 'dropped_claims': []}
                logger = JsonlLogger(run_id=identifier)
                logger.write('agent', 'startup_failed', ok=False, error_class=type(exc).__name__)
                emit({'event': 'done', 'timestamp': now(), 'investigation_id': identifier, 'step': 'clarify',
                      'why': 'Startup dependencies were unavailable.', 'status': 'partial'})
            finally:
                state['finished'] = True
        self.worker.submit(work)
        return identifier


def create_app(*, run=investigate, reference=True, state_dir='.cache/state', log_dir='logs'):
    manager = Manager(run)
    @asynccontextmanager
    async def lifespan(app):
        server = ensure_reference_server(JsonlLogger(log_dir)) if reference else None
        try:
            if reference:
                from .config import load_settings
                from .zetaris import ZetarisClient
                with ZetarisClient(load_settings()) as client:
                    ensure_reference_table(client, JsonlLogger(log_dir))
            yield
        finally:
            manager.worker.shutdown(wait=True, cancel_futures=True)
            if server:
                server.shutdown()
                server.server_close()
    app = FastAPI(title='PolyToken', lifespan=lifespan)
    app.state.manager = manager

    def state(identifier):
        if identifier not in manager.runs:
            raise HTTPException(404, 'Investigation not found')
        return manager.runs[identifier]

    @app.post('/investigations', status_code=202)
    def start(payload: InvestigationRequest):
        if payload.company not in ('samudra', 'swara'):
            raise HTTPException(422, 'Unknown company')
        return {'id': manager.start(payload.model_dump())}

    @app.get('/investigations/{identifier}/events')
    async def events(identifier: str, request: Request):
        entry = state(identifier)
        try:
            cursor = int(request.headers.get('last-event-id', '-1')) + 1
            if cursor < 0:
                raise ValueError
        except ValueError:
            raise HTTPException(400, 'Invalid Last-Event-ID') from None
        async def stream():
            nonlocal cursor
            while True:
                with manager.lock:
                    batch = entry['events'][cursor:]
                    finished = entry['finished']
                for row in batch:
                    yield f'id: {cursor}\nevent: {row["event"]}\ndata: {json.dumps(row, ensure_ascii=False)}\n\n'
                    cursor += 1
                    await asyncio.sleep(0)
                if finished or await request.is_disconnected():
                    break
                if not batch:
                    yield ': waiting\n\n'
                    await asyncio.sleep(.1)
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache'})

    @app.get('/investigations/{identifier}/report')
    def report(identifier: str):
        if identifier in manager.runs:
            entry = state(identifier)
            if entry['report'] is None:
                raise HTTPException(202, 'Investigation is running')
            return JSONResponse(entry['report'], status_code=202 if entry['report'].get('status') == 'running' else 200)
        if not re.fullmatch(r'[A-Za-z0-9-]+', identifier):
            raise HTTPException(404, 'Investigation not found')
        path = Path(log_dir) / 'investigations' / (identifier + '.json')
        if not path.exists():
            raise HTTPException(404, 'Investigation not found')
        return json.loads(path.read_text())

    @app.get('/evidence/{identifier}')
    def evidence(identifier: str):
        with WorldModel(Path(state_dir) / 'world.sqlite', logger=JsonlLogger(log_dir)) as world:
            result = next((row for row in world.events() if row['event_id'] == identifier), None)
        if result is None:
            raise HTTPException(404, 'Evidence not found')
        return result

    @app.get('/companies')
    def companies():
        from .config import load_settings
        from .zetaris import ZetarisClient
        with ZetarisClient(load_settings()) as client:
            return [{k: v for k, v in client.query(f'SELECT * FROM company_systems.{company}__bot_config')[0].items()
                     if k in ('company', 'language', 'model_in_use', 'monthly_chats', 'latency_target_s')}
                    for company in ('samudra', 'swara')]
    mount_billing_api(app, manager, state_dir, log_dir)
    mount_ui(app)
    return app


def mount_ui(app):
    """Mount the checkout's no-build interface after the API routes."""
    from fastapi.staticfiles import StaticFiles

    app.mount('/', StaticFiles(directory=Path(__file__).resolve().parents[2] / 'web', html=True), name='ui')


def mount_billing_api(app, manager, state_dir, log_dir):
    """Register billing/display routes independently of the investigation worker."""
    from fastapi import Query
    from .billing_view import archived_events, build_billing, find_report, BillingUnavailable
    from .currencies import load_currencies
    from .tokens import token_pieces
    billing_cache = {}
    billing_lock = threading.Lock()

    @app.get('/currencies')
    def currencies():
        try:
            result = load_currencies()
            JsonlLogger(log_dir).write('currencies', 'reference_loaded', ok=True, base=result['base'], rates=result['rates'], source='data/reference/fx.json')
            return result
        except (ValueError, KeyError, OSError):
            raise HTTPException(503, 'Verified display currencies are unavailable') from None

    @app.get('/investigations/{identifier}/billing')
    def billing(identifier: str):
        try:
            report = find_report(identifier, manager, log_dir)
        except FileNotFoundError:
            raise HTTPException(404, 'Investigation not found') from None
        if report is None:
            return JSONResponse({'id': identifier, 'status': 'running', 'reason': 'No checked billing snapshot yet.'}, status_code=202)
        logger = JsonlLogger(log_dir, run_id=identifier)
        records = {e['event_id']: e for e in archived_events(log_dir)}
        path = Path(state_dir) / 'world.sqlite'
        if path.is_file():
            with WorldModel(path, logger=logger) as world:
                # Runtime rows take precedence so an archive cannot mask tampering.
                records.update({e['event_id']: e for e in world.events()})
        try:
            import hashlib
            wanted = set(report.get('evidence_ids', []))
            for claim in report.get('claims', []):
                wanted.update(claim.get('evidence_ids', []))
            pending = list(wanted)
            while pending:
                row = records.get(pending.pop())
                for parent in (row or {}).get('payload', {}).get('supports', []):
                    if parent not in wanted:
                        wanted.add(parent)
                        pending.append(parent)
            # Include actual content, not only its declared ID, in cache identity.
            fingerprint = hashlib.sha256(json.dumps([report, [records.get(k) for k in sorted(wanted)]], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            with billing_lock:
                if fingerprint in billing_cache:
                    logger.write('billing', 'checked_view_reused', ok=True, fingerprint=fingerprint)
                    return billing_cache[fingerprint]
            result = build_billing(report, list(records.values()), logger=logger)
            with billing_lock:
                if len(billing_cache) >= 8:
                    billing_cache.pop(next(iter(billing_cache)))
                billing_cache[fingerprint] = result
            return result
        except (BillingUnavailable, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
            reason = logger.redact(str(exc))
            logger.write('billing', 'unavailable', ok=False, reason=reason)
            return {'id': identifier, 'status': 'not measured', 'reason': reason, 'claims': []}

    @app.get('/tokens')
    def tokens(text: str = Query(min_length=1, max_length=2000), tokenizer: str = Query(min_length=1, max_length=200)):
        logger = JsonlLogger(log_dir)
        try:
            result = token_pieces(tokenizer, text)
        except ValueError as exc:
            logger.write('token_strip', 'measurement_failed', ok=False, tokenizer=tokenizer, reason=logger.redact(str(exc)))
            raise HTTPException(422, logger.redact(str(exc))) from None
        except Exception as exc:
            logger.write('token_strip', 'measurement_failed', ok=False, tokenizer=tokenizer, error_class=type(exc).__name__)
            return {'ok': False, 'tokenizer': tokenizer, 'reason': 'Local tokenizer could not be read; no download attempted.'}
        import hashlib
        source = dict(kind='Local tokenizer measurement', source=result.get('source', 'Local tokenizer cache'),
                      at=now(), fetched_at=now(), query='GET /tokens; UTF-8 text SHA-256 '+hashlib.sha256(text.encode()).hexdigest(),
                      time_window={'start': now(), 'end': now()}, run_id=logger.run_id)
        if result['ok']:
            with WorldModel(Path(state_dir) / 'world.sqlite', logger=logger) as world:
                identifier = world.evidence_event('measurement', source['query']+' '+tokenizer, result, source)
            result = {**result, 'evidence_id': identifier, 'provenance': source}
        logger.write('token_strip', 'measured', **{**result, 'provenance': source})
        return result
