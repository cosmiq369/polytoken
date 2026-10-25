"""Console integrity, causal spans, cancellation, replay and price resilience."""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from polytoken.agent.budget import BudgetGuard, BudgetExceeded
from polytoken.agent.jobs import JobBudget
from polytoken.agent.runner import Investigation
from polytoken.agent.telemetry import safe_explanation
from polytoken.api import create_app
from test_agent import apparatus


@pytest.mark.parametrize('text', ['Saving 87.92 INR/month', 'Savings are ₹8,785.60', 'సేవింగ్ ౮౭.౯౨', 'eighty percent cheaper', 'half the cost', 'one million tokens'])
def test_numeric_planner_prose_cannot_reach_step_text(text):
    result = safe_explanation(text)
    assert text != result
    assert not any(c.isnumeric() for c in result)


def test_span_pairs_parents_redaction_and_verified_findings(apparatus):
    a = apparatus
    original = a['generator']
    def generate(prompt, **kwargs):
        result = original(prompt, **kwargs)
        if 'Return only JSON' in prompt:
            data = json.loads(result['text'])
            data['why'] = 'English system substitution shows 87.92 INR/month saving'
            result['text'] = json.dumps(data)
        return result
    a['tools'].generate = generate
    agent = Investigation(a['tools'], a['memory'])
    report = agent.run('samudra')
    assert report['status'] == 'complete'
    assert not any('87.92' in e.get('why', '') or '87.92' in e.get('text', '') for e in agent.events)
    starts = {e['span_id']: e for e in agent.events if e['event'] in ('tool_started', 'model_call_started', 'sql_started')}
    finishes = {e['span_id']: e for e in agent.events if e['event'] in ('tool_finished', 'model_call_finished', 'sql_finished')}
    assert starts.keys() == finishes.keys()
    assert all(e['duration_ms'] >= 0 for e in finishes.values())
    assert all(starts[e['span_id']]['timestamp'] <= e['timestamp'] for e in finishes.values())
    sql = next(e for e in starts.values() if e['event'] == 'sql_started')
    assert starts[sql['parent_id']]['service'] == 'tools'
    assert {'planner', 'judge', 'hosted'} <= {e.get('role') for e in starts.values()}
    assert all(e['claim']['verified'] for e in agent.events if e['event'] == 'claim_verified')
    assert any(e['event'] == 'claim_verified' and e['step'] == 'measure' for e in agent.events)
    assert all(e['ceilings']['judge'] == 45 for e in agent.events if e['event'] == 'budget')
    log = (a['tools'].logger.directory / 'agent_events.jsonl').read_text()
    assert 'fixture-nvidia-secret' not in log


@pytest.mark.parametrize('failures', [1, 2])
def test_price_read_retries_then_keeps_nonmoney_claims(apparatus, failures):
    a = apparatus
    original = a['sql'].query
    attempts = 0
    def query(sql, **kwargs):
        nonlocal attempts
        if '.prices' in sql:
            attempts += 1
            if attempts <= failures:
                kwargs['before_attempt']()
                raise RuntimeError('Price source unavailable')
        return original(sql, **kwargs)
    a['sql'].query = query
    report = Investigation(a['tools'], a['memory']).run('samudra')
    assert attempts == 2
    assert any(c['id'].endswith('/system_prompt_share') for c in report['claims'])
    money = [c for c in report['claims'] if c['unit'] == 'INR']
    assert bool(money) == (failures == 1)


def test_cancel_reaches_background_budget():
    event = threading.Event()
    reasoning = BudgetGuard(cancel_event=event)
    background = JobBudget(reasoning)
    event.set()
    for budget in (reasoning, background):
        with pytest.raises(BudgetExceeded, match='Stopped by user'):
            budget.consume('hosted')
    assert reasoning.counts['hosted'] == 0


def test_stop_live_fake_run_and_idempotence(tmp_path):
    entered = threading.Event()
    def fake(company, *, run_id, event_sink, cancel_event, **kwargs):
        entered.set()
        event_sink(dict(event='step_started', step='measure', timestamp='2026-10-25T00:00:00Z', investigation_id=run_id))
        assert cancel_event.wait(3)
        event_sink(dict(event='done', step='report', timestamp='2026-10-25T00:00:01Z', investigation_id=run_id, status='partial'))
        return dict(id=run_id, status='partial', claims=[], dropped_claims=[], partial_reason='Stopped by user'), []
    app = create_app(run=fake, reference=False, state_dir=tmp_path, log_dir=tmp_path)
    with TestClient(app) as client:
        identifier = client.post('/investigations', json={'company': 'samudra'}).json()['id']
        assert entered.wait(3)
        assert client.post(f'/investigations/{identifier}/stop').status_code == 202
        for _ in range(100):
            if app.state.manager.runs[identifier]['finished']:
                break
            time.sleep(.01)
        assert app.state.manager.runs[identifier]['finished']
        assert client.get(f'/investigations/{identifier}/report').json()['partial_reason'] == 'Stopped by user'
        assert client.post(f'/investigations/{identifier}/stop').json()['status'] == 'finished'
        assert client.post('/investigations/missing/stop').status_code == 404
    assert 'stop_requested' in (tmp_path / 'agent_events.jsonl').read_text()


def test_demo_is_offline_and_replay_rechecks_sources(tmp_path):
    sample = tmp_path / 'sample'
    sample.mkdir()
    (sample / 'demo_report.json').write_text(json.dumps(dict(id='demo-test',company='samudra',status='complete',claims=[dict(id='forged',value=99,verified=True,evidence_ids=['missing'])])))
    (sample / 'demo.jsonl').write_text(json.dumps(dict(event='step_started',timestamp='2026-10-25T00:00:00Z',investigation_id='demo-test',step='measure',why='87.92 INR saved'))+'\n')
    with TestClient(create_app(reference=False,demo=True,log_dir=tmp_path,state_dir=tmp_path)) as client:
        assert client.get('/console/config').json()['demo'] is True
        assert client.post('/investigations',json={'company':'samudra'}).status_code == 409
        assert client.get('/companies').json() == []
        replay=client.get('/investigations/demo-test/replay').json()
        assert replay['report']['claims'] == []
        assert replay['report']['dropped_claims'][0]['id'] == 'forged'
        assert '87.92' not in replay['events'][0]['why']
        assert replay['legacy'] is True


def test_cancel_queued_run_never_calls_generator(tmp_path):
    entered = threading.Event()
    release = threading.Event()
    calls = []
    def fake(company, *, run_id, **kwargs):
        calls.append(run_id)
        entered.set()
        assert release.wait(3)
        return dict(id=run_id, status='complete', claims=[]), []
    app = create_app(run=fake, reference=False, state_dir=tmp_path, log_dir=tmp_path)
    with TestClient(app) as client:
        first = client.post('/investigations', json={'company': 'samudra'}).json()['id']
        assert entered.wait(3)
        second = client.post('/investigations', json={'company': 'swara'}).json()['id']
        client.post(f'/investigations/{second}/stop')
        release.set()
        for _ in range(100):
            if app.state.manager.runs[second]['finished']:
                break
            time.sleep(.01)
        assert calls == [first]
        assert client.get(f'/investigations/{second}/report').json()['partial_reason'] == 'Stopped by user'
