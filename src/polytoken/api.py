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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from .launcher import Launch, MAX_BYTES

from .agent.runtime import investigate
from .logs import JsonlLogger
from .meterless.world_model import WorldModel
from .reference_server import ensure_reference_server, ensure_reference_table
from .tools import now


class InvestigationRequest(BaseModel):
    company: str
    question: str = Field(default='', max_length=1000)
    launch: Launch | None = None
    monthly_chats: int | None = Field(default=None, gt=0)
    latency_target_s: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class Manager:
    def __init__(self, run=investigate, log_dir="logs"):
        self.run = run
        self.log_dir = log_dir
        self.runs = {}
        self.lock = threading.Lock()
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='investigation')

    def start(self, payload):
        identifier = uuid4().hex
        state = {'events': [], 'report': None, 'finished': False, 'cancel_event': threading.Event(),
                 'company': payload['company'], 'created_at': now()}
        with self.lock:
            self.runs[identifier] = state
        def emit(row):
            with self.lock:
                state['events'].append(row)
        def work():
            try:
                if state['cancel_event'].is_set():
                    raise RuntimeError('Stopped before execution')
                def publish(report):
                    with self.lock:
                        state['report'] = report
                        state['company'] = report.get('company', state['company'])
                import inspect
                extra = {'report_sink': publish} if 'report_sink' in inspect.signature(self.run).parameters else {}
                if 'cancel_event' in inspect.signature(self.run).parameters:
                    extra['cancel_event'] = state['cancel_event']
                report, _ = self.run(**payload, run_id=identifier, event_sink=emit, **extra)
                state['report'] = report
                state['company'] = report.get('company', state['company'])
            except Exception as exc:
                state['report'] = {'id': identifier, 'status': 'partial', 'partial_reason': 'Stopped by user' if state['cancel_event'].is_set() else 'startup failed: ' + type(exc).__name__,
                                   'claims': [], 'dropped_claims': []}
                logger = JsonlLogger(self.log_dir, run_id=identifier)
                logger.write('agent', 'startup_failed', ok=False, error_class=type(exc).__name__)
                row = {'event': 'done', 'timestamp': now(), 'investigation_id': identifier, 'step': 'clarify',
                       'why': 'Stopped before execution.' if state['cancel_event'].is_set() else 'Startup dependencies were unavailable.', 'status': 'partial'}
                logger.write('agent_events', **row)
                emit(row)
            finally:
                state['finished'] = True
        self.worker.submit(work)
        return identifier


def create_app(*, run=investigate, reference=True, state_dir='.cache/state', log_dir='logs', demo=False):
    if run is investigate:
        from functools import partial
        run = partial(investigate, log_dir=log_dir, state_dir=state_dir)
    manager = Manager(run, log_dir)
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
    app.add_middleware(CORSMiddleware, allow_origin_regex=r'http://localhost(?::[0-9]+)?',
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'Last-Event-ID'])
    app.state.manager = manager
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def invalid_payload(request, exc):
        # Validation must never echo uploaded conversations or arbitrary values.
        errors = '; '.join('.'.join(str(p) for p in e['loc'][1:]) + ': ' + e['msg'] for e in exc.errors())
        return JSONResponse({'detail': errors}, status_code=422)

    @app.middleware('http')
    async def bound_request(request, call_next):
        if request.method == 'POST':
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BYTES * 2:
                    return JSONResponse({'detail': 'Request too large; sample limit is one MiB.'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        return await call_next(request)

    @app.get('/launcher/options')
    def launcher_options():
        from .launcher import priced_models
        from .console_api import demo_companies
        return {'demo': demo, 'models': priced_models(), 'samples': demo_companies(log_dir), 'max_bytes': MAX_BYTES}


    def state(identifier):
        if identifier not in manager.runs:
            raise HTTPException(404, 'Investigation not found')
        return manager.runs[identifier]

    @app.post('/investigations', status_code=202)
    def start(payload: InvestigationRequest):
        if demo:
            if payload.launch is None or not payload.launch.sample:
                raise HTTPException(409, 'Live mode needed. Uploaded data cannot run in demo mode.')
            from .console_api import reports
            saved = [r for r in reports(log_dir).values() if r.get('company') == payload.launch.sample and r.get('model_fit') and r.get('status') == 'complete']
            if not saved:
                raise HTTPException(409, 'No checked saved run is available for this bundled sample')
            preferred = Path(log_dir) / 'sample' / f'agent_{payload.launch.sample}_model_fit_report.json'
            identifier = json.loads(preferred.read_text())['id'] if preferred.exists() else saved[-1]['id']
            bundle = app.state.load_replay(identifier)
            with manager.lock:
                manager.runs[identifier] = {'company': payload.launch.sample, 'events': bundle['events'],
                    'report': bundle['report'], 'finished': True, 'cancel_event': threading.Event(), 'replay': True}
            JsonlLogger(log_dir).write('launcher', 'replay_started', ok=True, investigation_id=identifier,
                note='Saved configuration and numbers retained; form edits do not modify archived evidence')
            return {'id': identifier, 'mode': 'replay', 'label': 'Replay of a saved run',
                    'note': 'Uses the saved company, models and volume. Form edits do not change this replay.'}
        if payload.launch:
            return {'id': manager.start({'company': payload.company, 'launch': payload.launch.model_dump()}), 'mode': 'live'}
        if payload.company not in ('samudra', 'swara', 'raitu', 'paisa'):
            raise HTTPException(422, 'Unknown company')
        return {'id': manager.start(payload.model_dump(exclude={'launch'})), 'mode': 'live'}

    @app.post('/investigations/{identifier}/stop', status_code=202)
    def stop(identifier: str):
        entry = state(identifier)
        with manager.lock:
            if entry['finished']:
                return {'id': identifier, 'status': 'finished'}
            entry['cancel_event'].set()
        logger = JsonlLogger(log_dir, run_id=identifier)
        row = {'event': 'stop_requested', 'timestamp': now(), 'investigation_id': identifier,
               'step': 'stop', 'why': 'Stop requested. Waiting for the current bounded call to return.'}
        with manager.lock:
            entry['events'].append(row)
        logger.write('agent_events', **row)
        return {'id': identifier, 'status': 'stopping'}

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
            from .billing_view import archived_events
            result = next((r for r in archived_events(log_dir) if r['event_id'] == identifier), None)
        if result is None:
            raise HTTPException(404, 'Evidence not found')
        return result

    @app.get('/companies')
    def companies():
        if demo:
            from .console_api import demo_companies
            return demo_companies(log_dir)
        from .config import load_settings
        from .zetaris import ZetarisClient
        from .console_api import reports
        from .launcher import valid_company
        known = {'samudra', 'swara', 'raitu', 'paisa'}
        known.update(r['company'] for r in reports(log_dir).values() if valid_company(r.get('company', '')))
        with ZetarisClient(load_settings()) as client:
            return [{k: v for k, v in client.query(f'SELECT * FROM company_systems.{company}__bot_config')[0].items()
                     if k in ('company', 'language', 'model_in_use', 'monthly_chats', 'latency_target_s', 'role', 'channel', 'current_model', 'dataset_version', 'display_name')}
                    for company in sorted(known)]
    mount_billing_api(app, manager, state_dir, log_dir)
    from .console_api import mount_console
    mount_console(app, manager, log_dir, state_dir, demo)
    mount_ui(app)
    return app


def mount_ui(app):
    """Mount the checkout's no-build interface after the API routes."""
    from fastapi.staticfiles import StaticFiles

    from .paths import ROOT
    app.mount('/', StaticFiles(directory=ROOT / 'web', html=True), name='ui')


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

    @app.get('/token-samples')
    def token_samples():
        from .token_samples import samples
        return samples(log_dir, JsonlLogger(log_dir))

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
