"""Offline archive discovery and replay. No provider calls or static log exposure."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

from .agent.telemetry import safe_explanation
from .billing_view import archived_events, find_report, EventWorld
from .checker import Checker
from .logs import JsonlLogger
from .meterless.world_model import WorldModel


def reports(log_dir):
    found = {}
    for folder, pattern in [('sample', '*_report.json'), ('investigations', '*.json')]:
        for path in sorted((Path(log_dir) / folder).glob(pattern)):
            try:
                row = json.loads(path.read_text())
                if row.get('id') and isinstance(row.get('claims'), list):
                    found[row['id']] = row
            except (ValueError, OSError):
                continue
    return found


def demo_companies(log_dir):
    rows = archived_events(log_dir)
    result = {}
    for row in rows:
        config = row.get('payload', {}).get('config', {})
        if config.get('company') in ('samudra', 'swara', 'raitu', 'paisa') and (config.get('dataset_version') or not result.get(config['company'], {}).get('dataset_version')):
            result[config['company']] = {k: v for k, v in config.items() if k in ('company', 'language', 'model_in_use', 'monthly_chats', 'latency_target_s', 'role', 'channel', 'current_model', 'dataset_version')}
    return list(result.values())


def mount_console(app, manager, log_dir, state_dir, demo):
    @app.get('/console/config')
    def config():
        return {'demo': demo}

    @app.get('/investigations')
    def history():
        found = reports(log_dir)
        preferred = set()
        new_names = tuple(f'agent_{c}_model_fit_report.json' for c in ('samudra', 'swara', 'raitu', 'paisa'))
        names = new_names if any((Path(log_dir) / 'sample' / n).exists() for n in new_names) else ('demo_samudra_report.json', 'agent_swara_v3_report.json')
        for name in names:
            path = Path(log_dir) / 'sample' / name
            if path.exists():
                preferred.add(json.loads(path.read_text())['id'])
        result = {key: {'demo': key in preferred, 'id': key, 'company': r.get('company'), 'display_name': (r.get('model_fit') or {}).get('profile', {}).get('display_name'), 'status': r.get('status'), 'saved': True}
                  for key, r in found.items()}
        with manager.lock:
            for key, entry in manager.runs.items():
                result[key] = {'id': key, 'company': entry.get('company'),
                               'display_name': ((entry.get('report') or {}).get('model_fit') or {}).get('profile', {}).get('display_name'),
                               'status': (entry.get('report') or {}).get('status', 'running' if entry['events'] else 'queued'),
                               'saved': entry.get('finished', False)}
        return list(result.values())

    def fit_records():
        records = {e['event_id']: e for e in archived_events(log_dir)}
        path = Path(state_dir) / 'world.sqlite'
        if path.exists():
            with WorldModel(path, logger=JsonlLogger(log_dir)) as world:
                records.update({e['event_id']: e for e in world.events()})
        return EventWorld(records.values())

    @app.get('/model-fits')
    def model_fits():
        from .model_fit import replay_fit
        world = fit_records()
        selected = {}
        logger = JsonlLogger(log_dir)
        for report in reports(log_dir).values():
            if report.get('status') != 'complete' or not report.get('model_fit'):
                continue
            view, claims = replay_fit(report, world, logger)
            if not view:
                continue
            snapshot_id = claims[0]['recompute']['inputs']['snapshot']
            stamp = world.records[snapshot_id]['provenance']['fetched_at']
            company = report['company']
            if company not in selected or stamp > selected[company]['fetched_at']:
                selected[company] = dict(company=company, id=report['id'], model_fit=view, claims=claims, fetched_at=stamp)
        order = [c for c in ('samudra', 'swara', 'raitu', 'paisa') if c in selected]
        return [selected[c] for c in [*order, *sorted(set(selected) - set(order))]]

    @app.get('/investigations/{identifier}/model-fit')
    def model_fit(identifier: str):
        from .model_fit import replay_fit
        try:
            report = find_report(identifier, manager, log_dir)
        except FileNotFoundError:
            raise HTTPException(404, 'Saved run not found') from None
        view, claims = replay_fit(report or {}, fit_records(), JsonlLogger(log_dir))
        if not view:
            raise HTTPException(409, 'No fully checked model-fit evidence for this run')
        return dict(id=identifier, model_fit=view, claims=claims)

    @app.get('/investigations/{identifier}/replay')
    def replay(identifier: str):
        try:
            report = find_report(identifier, manager, log_dir)
        except FileNotFoundError:
            raise HTTPException(404, 'Saved run not found') from None
        if report is None or report.get('status') == 'running':
            raise HTTPException(409, 'Run is still active')
        events = []
        paths = [Path(log_dir) / 'agent_events.jsonl', *(Path(log_dir) / 'sample').glob('*.jsonl')]
        seen = set()
        for path in paths:
            if not path.is_file() or 'world_events' in path.name or '_audit_' in path.name:
                continue
            for line in path.read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                allowed = {'step_started', 'step_finished', 'planner_reason', 'tool_called', 'tool_started', 'tool_finished', 'model_call_started', 'model_call_finished', 'sql_started', 'sql_finished', 'claim_verified', 'evidence_added', 'finding', 'budget', 'claim_dropped', 'experiment_progress', 'experiment_done', 'price_unavailable', 'stop_requested', 'done'}
                if row.get('event') not in allowed or not row.get('timestamp') or row.get('investigation_id') != identifier:
                    continue
                # Archives may duplicate the same event with logger metadata.
                row.pop('ts', None)
                row.pop('run_id', None)
                key = json.dumps(row, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    events.append(row)
        events.sort(key=lambda e: e.get('timestamp', ''))
        records = {e['event_id']: e for e in archived_events(log_dir)}
        path = Path(state_dir) / 'world.sqlite'
        if path.exists():
            with WorldModel(path, logger=JsonlLogger(log_dir)) as world:
                records.update({e['event_id']: e for e in world.events()})
        wanted = set(report.get('evidence_ids', []))
        wanted.update(e.get('evidence_id') for e in events if e.get('evidence_id'))
        for claim in report['claims']:
            wanted.update(claim.get('evidence_ids', []))
        pending = list(wanted)
        while pending:
            for parent in records.get(pending.pop(), {}).get('payload', {}).get('supports', []):
                if parent not in wanted:
                    wanted.add(parent)
                    pending.append(parent)
        evidence = [records[k] for k in wanted if k in records]
        logger = JsonlLogger(log_dir, run_id=identifier)
        checked, dropped = Checker(SimpleNamespace(world=EventWorld(evidence)), logger).check(report['claims'])
        from .model_fit import replay_fit
        fit, _ = replay_fit(report, EventWorld(evidence), logger)
        report = {**copy.deepcopy(report), 'model_fit': fit, 'claims': checked, 'dropped_claims': [*report.get('dropped_claims', []), *dropped]}
        valid = {c['id']: c for c in checked}
        cleaned = []
        for row in events:
            row = dict(row)
            for field in ('why', 'text'):
                if field in row:
                    row[field] = safe_explanation(row[field])
            if row['event'] == 'claim_verified':
                claim = row.get('claim', {})
                if claim.get('id') not in valid or claim.get('value') != valid[claim['id']]['value']:
                    continue
                row['claim'] = valid[claim['id']]
            cleaned.append(row)
        logger.write('console', 'replay_loaded', ok=True, event_count=len(cleaned), checked_claims=len(checked))
        return logger.redact({'report': report, 'events': cleaned, 'evidence': evidence,
                              'legacy': not any(e.get('span_id') for e in events)})

    app.state.load_replay = replay

    from pydantic import BaseModel, Field
    class AskRequest(BaseModel):
        question: str = Field(min_length=1, max_length=1000)
        compare_id: str | None = Field(default=None, max_length=100)

    @app.post('/investigations/{identifier}/ask')
    def ask(identifier: str, payload: AskRequest):
        from .ask import answer
        try:
            report = find_report(identifier, manager, log_dir)
            other = find_report(payload.compare_id, manager, log_dir) if payload.compare_id else None
        except FileNotFoundError:
            raise HTTPException(404, 'Saved run not found') from None
        return answer(payload.question, report or {}, fit_records(), JsonlLogger(log_dir), other=other)
