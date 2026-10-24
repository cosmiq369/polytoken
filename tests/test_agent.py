import builtins
import copy
import json
from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from polytoken.agent.budget import BudgetGuard, BudgetExceeded
from polytoken.agent.calculations import items_from_rows
from polytoken.agent.planner import Planner, validate_plan
from polytoken.agent.runner import Investigation, STEPS
from polytoken.api import create_app
from polytoken.checker import Checker, make_claims
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.hmem import HMem
from polytoken.meterless.markovian import run_efficiency, ChunkConfig
from polytoken.meterless.world_model import WorldModel
from polytoken.reference import load_fx, load_hosted
from polytoken.tools import InvestigationTools, validate_sql


@pytest.fixture
def apparatus(tmp_path, logger):
    spec = 'fixture/model'
    config = dict(company='samudra', language='te', system_prompt_native='native policy ' * 80,
                  system_prompt_en='English policy', model_in_use=spec, monthly_chats=100000, latency_target_s=2., review_status='pending')
    chats = [dict(chat_id=f'chat_{i:03d}', turn=t, role='user' if t % 2 else 'assistant',
                  text_native=f'native text {i} {t}', text_en=f'English text {i} {t}', lang='te')
             for i in range(50) for t in range(1, 5)]
    items = items_from_rows('samudra', config, chats)
    counts = [{**{k: r[k] for k in ('company', 'chat_id', 'turn', 'part')}, 'tokenizer_spec': spec,
               'lang_variant': lang, 'tokens': len(r[v].split()), 'run_id': 'fixture'}
              for r in items for v, lang in (('native', 'te'), ('en', 'en'))]
    price = dict(model='fixture/model', provider='fixture', tokenizer_spec=spec,
                 input_per_mtok_usd=2., output_per_mtok_usd=4., source_url='https://example.test/price',
                 fetched_at='2026-10-24T00:00:00Z', verified=True)
    class SQL:
        calls = []
        def query(self, query, **kwargs):
            kwargs['before_attempt']()
            self.calls.append(query)
            if 'bot_config' in query:
                return [copy.deepcopy(config)]
            if '__chats' in query:
                return copy.deepcopy(chats)
            if 'latest_token_counts' in query:
                return copy.deepcopy(counts)
            if 'prices' in query:
                return [copy.deepcopy(price)]
            raise AssertionError(query)
    class Generate:
        calls = []
        def __call__(self, prompt, **kwargs):
            kwargs['before_attempt']()
            self.calls.append((prompt, kwargs))
            if 'Return only JSON' in prompt:
                context = json.loads(prompt.split('\n', 1)[1].split('\nRepair:')[0])
                step = context['step']
                args = context['allowed'][step][0]
                why = 'Rank expected savings using billed counts and verified prices.' if step == 'hypothesise' else 'Use the stored evidence for this step.'
                text = json.dumps(dict(why=why, tool=step, args=args, done=step == 'report'))
            elif 'Judge semantic equivalence' in prompt:
                pairs = json.loads(prompt.split('\n', 1)[1])
                text = json.dumps([dict(chat_id=p['chat_id'], same_facts=True, reason='Facts match.') for p in pairs])
            else:
                text = 'సరే same facts'
                kwargs['on_stream'](text)
            return dict(text=text, usage={'prompt_tokens': 100, 'completion_tokens': 25},
                        latency_s=1.5, ttft_s=.2, request_latency_s=1.4)
    world = WorldModel(storage='memory', logger=logger)
    memory = HMem(logger=logger)
    gen, sql, budget = Generate(), SQL(), BudgetGuard()
    tools = InvestigationTools(sql, gen, EvidenceStore(world), budget, logger,
        catalogue={'families': {'fixture/model': ['fixture/hosted'], 'other/model': ['other/hosted']}},
        prices=[price], fx=load_fx(), count=lambda spec, text: len(text.split()))
    yield dict(tools=tools, memory=memory, generator=gen, sql=sql, world=world, config=config)
    world.close()


def test_scripted_production_size_and_memory(apparatus):
    a = apparatus
    report = Investigation(a['tools'], a['memory']).run('samudra')
    assert report['status'] == 'complete', report['partial_reason']
    assert report['dropped_claims'] == []
    assert report['quality_status'] == 'automated pass; native review pending'
    assert report['speed_status'] == 'inconclusive'
    assert report['top_fix'] == 'english_system'
    assert a['tools'].budget.counts == {'nemotron': 13, 'hosted': 48, 'sql': 4}
    assert all(c['verified'] for c in report['claims'])
    assert len(a['tools'].snapshot['items']) == 201
    # A fresh guard and the same H-MEM must expose recalled fields.
    a['tools'].budget = BudgetGuard()
    second = Investigation(a['tools'], a['memory']).run('samudra')
    assert second['remembered'] and second['remembered_fields']


def test_no_hidden_file_reads_in_investigation(apparatus, monkeypatch):
    original = builtins.open
    path_open = Path.open
    def forbidden(path):
        if isinstance(path, (str, Path)):
            value = str(Path(path).absolute())
            assert not any(part in value for part in ('/docs/', '/data/demo/', '/scripts/', '/logs/sample/')), value
    def guarded(path, *args, **kwargs):
        if not args or 'r' in str(args[0]):
            forbidden(path)
        return original(path, *args, **kwargs)
    def guarded_path(path, *args, **kwargs):
        if not args or 'r' in str(args[0]):
            forbidden(path)
        return path_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', guarded)
    monkeypatch.setattr(Path, 'open', guarded_path)
    report = Investigation(apparatus['tools'], apparatus['memory']).run('samudra')
    assert report['status'] == 'complete'


@pytest.mark.parametrize('kind', ['nemotron', 'hosted', 'sql'])
def test_every_count_budget(kind):
    guard = BudgetGuard()
    for _ in range(guard.LIMITS[kind]):
        guard.consume(kind)
    with pytest.raises(BudgetExceeded):
        guard.consume(kind)
    assert guard.counts[kind] == guard.LIMITS[kind]


def test_wall_budget(clock):
    guard = BudgetGuard(clock=clock)
    clock.now = 360
    with pytest.raises(BudgetExceeded, match='wall'):
        guard.check()


def test_budget_causes_partial_report_and_marker(apparatus):
    t = apparatus['tools']
    t.budget.counts['nemotron'] = 25
    report = Investigation(t, apparatus['memory']).run('samudra')
    assert report['status'] == 'partial'
    assert report['partial_reason'] == 'nemotron call budget spent'
    assert t.budget.counts['nemotron'] == 25


@pytest.mark.parametrize('query', ['DELETE FROM company_systems.x', 'SELECT * FROM secrets.x',
    'SELECT * FROM company_systems.x; DROP TABLE x', 'SELECT * FROM company_systems.x JOIN secrets.x ON 1=1',
    'SELECT * FROM company_systems.x, secrets.x', 'SELECT secret() FROM company_systems.x',
    'WITH x AS (DELETE FROM company_systems.x) SELECT * FROM x', 'SELECT * FROM company_systems.x -- comment'])
def test_sql_allowlist(query):
    with pytest.raises(ValueError):
        validate_sql(query)


def test_tools_and_fail_closed_money(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    original = t.billed_cost('samudra', 'fixture/model')
    changed = t.billed_cost('samudra', 'fixture/model', 'english_system')
    assert changed['after_monthly_inr'] < original['before_monthly_inr']
    assert t.token_meter('samudra', 'assistant', 'native')['rows']
    assert t.token_meter('samudra', 'assistant', 'changed', texts=['a b c'], tokenizer='fixture/model')['rows'][0]['tokens'] == 3
    t.prices = []
    unavailable = t.billed_cost('samudra', 'fixture/model')
    assert unavailable['money_status'] == 'money unavailable'
    assert unavailable['before_monthly_inr'] is None


def test_checker_tampered_raw_measurement_drops_dependent_claims(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    result = t.measure('samudra', config, ids)
    inputs = dict(snapshot=t.snapshot_id, prices=t.price_id, fx=t.fx_id)
    claims = make_claims(result['metrics'], 'baseline', inputs)
    assert Checker(t.store).check(claims)[1] == []
    raw = next(e for e in apparatus['world'].events() if e['kind'] == 'query_result'
               and 'latest_token_counts' in str(e['provenance']['query']))
    raw['payload']['rows'][0]['tokens'] += 1
    apparatus['world'].db.execute('UPDATE events SET payload=? WHERE event_id=?', (json.dumps(raw['payload']), raw['event_id']))
    accepted, dropped = Checker(t.store).check(claims)
    assert not accepted and len(dropped) == len(claims)
    assert all('tampered' in d['reason'] for d in dropped)


def test_planner_repair_then_fallback(logger):
    fallback = dict(why='Use evidence.', tool='measure', args={}, done=False)
    invalid = dict(fallback, why='word ' * 41)
    with pytest.raises(ValueError):
        validate_plan(json.dumps(invalid), {'measure': [{}]})
    values = iter(['bad', json.dumps(fallback)])
    planner = Planner(lambda _: {'text': next(values)}, logger)
    assert planner.plan('measure', {}, fallback, {'measure': [{}]}) == fallback
    calls = []
    planner = Planner(lambda prompt: calls.append(prompt) or {'text': '[TASK_COMPLETE]'}, logger)
    assert planner.plan('measure', {}, fallback, {'measure': [{}]}) == fallback
    assert len(calls) == 2


def test_signed_negative_savings():
    metrics = run_efficiency([{'tokens': 100}], ChunkConfig(carryoverTokens=512))
    assert metrics['tokensSaved'] == 0
    assert metrics['net_tokens'] == -512 and metrics['net_percent'] == -512.


def test_unverified_reference_loaders(tmp_path):
    for load in (load_fx, load_hosted):
        path = tmp_path / 'ref.json'
        path.write_text(json.dumps({'verified': False}))
        with pytest.raises(ValueError, match='Unverified'):
            load(path)


def test_sse_order_and_reconnect(apparatus, tmp_path):
    def scripted(company, run_id, event_sink, **kwargs):
        agent = Investigation(apparatus['tools'], apparatus['memory'], run_id=run_id, event_sink=event_sink)
        return agent.run(company), agent.events
    # SQLite fixture connection belongs to the test thread; build the full run
    # there and replay its events through the API's actual worker.
    agent = Investigation(apparatus['tools'], apparatus['memory'])
    report = agent.run('samudra')
    def replay(company, run_id, event_sink, **kwargs):
        for row in agent.events:
            event_sink({**row, 'investigation_id': run_id})
        return {**report, 'id': run_id}, agent.events
    with TestClient(create_app(run=replay, reference=False, state_dir=tmp_path, log_dir=tmp_path)) as client:
        response = client.post('/investigations', json={'company': 'samudra', 'question': 'Why?'})
        assert response.status_code == 202
        identifier = response.json()['id']
        stream = client.get(f'/investigations/{identifier}/events')
        rows = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith('data: ')]
        assert rows[-1]['event'] == 'done'
        assert [r['step'] for r in rows if r['event'] == 'step_started'] == list(STEPS)
        assert all('why' in r and 'timestamp' in r for r in rows)
        assert client.get(f'/investigations/{identifier}/report').json()['status'] == 'complete'
        replayed = client.get(f'/investigations/{identifier}/events', headers={'Last-Event-ID': str(len(rows)-2)})
        assert replayed.text.count('data: ') == 1
        assert client.post('/investigations', json={'company': '../oops'}).status_code == 422


def test_stand_in_label_and_temperature(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    t.catalogue = {'families': {'unrelated': ['standin/hosted']}}
    experiment = t.fix_experiment('samudra', 'answer_cap')
    assert experiment['model_label'] == 'tested on a stand-in model'
    assert experiment['tokenizer_spec'] == 'fixture/model'
    calls = [kwargs for _, kwargs in apparatus['generator'].calls if kwargs.get('model')]
    assert len(calls) == 40 and all(c['temperature'] == 0 and c['model'] == 'standin/hosted' for c in calls)
    assert all(p['review_status'] == 'pending' for p in experiment['pairs'])


def test_model_switch_keeps_original_prompt(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    result = t.fix_experiment('samudra', 'model_switch', 'other/hosted')
    assert result['systems']['original'] == result['systems']['changed']
    assert result['models']['original'] != result['models']['changed']
    with pytest.raises(ValueError, match='same hosted'):
        t.fix_experiment('samudra', 'english_system', 'other/hosted')
    with pytest.raises(ValueError, match='allowlist'):
        t.fix_experiment('samudra', 'answer_cap', 'invented/model')


def test_judge_malformed_is_never_passed(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    result = t.fix_experiment('samudra', 'english_system')
    t.generate = lambda *a, **k: {'text': 'not JSON'}
    quality = t.quality_judge(result['pairs'])
    assert len(quality['pairs']) == 20
    assert all(p['same_facts'] is None and p['review_status'] == 'pending' for p in quality['pairs'])


def test_failed_hosted_call_is_a_failed_row(apparatus):
    t = apparatus['tools']
    def fail(*args, **kwargs):
        kwargs['before_attempt']()
        raise RuntimeError('fixture failure')
    t.generate = fail
    row = t._hosted_call('user', 'system', 'fixture/hosted', 'fixture/model')
    assert row['ok'] is False and 'output_tokens' not in row


def test_checker_wrong_value_and_missing_evidence(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    result = t.measure('samudra', config, ids)
    claims = make_claims(result['metrics'], 'baseline', dict(snapshot=t.snapshot_id, prices=t.price_id, fx=t.fx_id))
    claims[0]['value'] += 1
    claims[1]['evidence_ids'] = []
    accepted, dropped = Checker(t.store).check(claims)
    assert len(dropped) == 2
    assert len(accepted) == len(claims) - 2


def test_physical_retry_count_and_direct_json_mode(settings, logger, clock):
    import httpx
    from polytoken.llm import NvidiaGenerator, SlidingWindowLimiter
    calls = []
    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(429, headers={'Retry-After': '1'})
        return httpx.Response(200, json={'choices': [{'message': {'content': '{}'}}],
                                       'usage': {'prompt_tokens': 10, 'completion_tokens': 2}})
    guard = BudgetGuard(clock=clock)
    with NvidiaGenerator(settings, logger=logger, client=httpx.Client(transport=httpx.MockTransport(handle)),
                         limiter=__import__('polytoken.llm', fromlist=['SlidingWindowLimiter']).SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep),
                         clock=clock, sleep=clock.sleep, jitter=lambda: 0) as generator:
        result = generator.generate('Return JSON.', enable_thinking=False, reasoning_effort='low',
                                    before_attempt=lambda: guard.consume('nemotron'), remaining=guard.remaining)
    assert result['text'] == '{}'
    assert guard.counts['nemotron'] == 2
    assert all(c['chat_template_kwargs'] == {'enable_thinking': False} for c in calls)
    assert all(c['reasoning_effort'] == 'low' for c in calls)
    assert all(c['model'] == settings.agent_model for c in calls)


def test_budget_block_is_not_logged_as_a_physical_attempt(settings, logger, clock):
    import httpx
    from polytoken.llm import NvidiaGenerator, SlidingWindowLimiter
    def should_not_send(request):
        raise AssertionError('budget-blocked request reached the transport')
    guard = BudgetGuard(clock=clock)
    guard.counts['nemotron'] = 25
    with NvidiaGenerator(settings, logger=logger, client=httpx.Client(transport=httpx.MockTransport(should_not_send)),
                         limiter=SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep)) as generator:
        with pytest.raises(BudgetExceeded):
            generator.generate('test', before_attempt=lambda: guard.consume('nemotron'))
    row = json.loads((logger.directory / 'llm_calls.jsonl').read_text().splitlines()[-1])
    assert row['attempted'] is False
    assert guard.counts['nemotron'] == 25


@pytest.mark.parametrize('factor,should_pass', [(1e-10, True), (1e-8, False)])
def test_checker_ratio_tolerance(apparatus, factor, should_pass):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    result = t.measure('samudra', config, ids)
    claims = make_claims(result['metrics'], 'baseline', dict(snapshot=t.snapshot_id, prices=t.price_id, fx=t.fx_id))
    claim = next(c for c in claims if c['id'].endswith('/native_to_english_ratio'))
    claim['value'] *= 1 + factor
    accepted, dropped = Checker(t.store).check([claim])
    assert bool(accepted) is should_pass
    assert bool(dropped) is not should_pass


@pytest.mark.parametrize('delta,should_pass', [(.009, True), (.011, False)])
def test_checker_money_tolerance(apparatus, delta, should_pass):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    result = t.measure('samudra', config, ids)
    claims = make_claims(result['metrics'], 'baseline', dict(snapshot=t.snapshot_id, prices=t.price_id, fx=t.fx_id))
    claim = next(c for c in claims if c['id'].endswith('/monthly_inr'))
    claim['value'] += delta
    accepted, dropped = Checker(t.store).check([claim])
    assert bool(accepted) is should_pass
    assert bool(dropped) is not should_pass


def test_persisted_cli_uuid_report_and_path_validation(tmp_path):
    identifier = '66f0a95a-adf4-4540-b4c7-12f5a03cef2d'
    directory = tmp_path / 'investigations'
    directory.mkdir()
    report = {'id': identifier, 'status': 'partial', 'claims': []}
    (directory / (identifier + '.json')).write_text(json.dumps(report))
    with TestClient(create_app(reference=False, log_dir=tmp_path, state_dir=tmp_path)) as client:
        assert client.get(f'/investigations/{identifier}/report').json() == report
        assert client.get('/investigations/invalid.name/report').status_code == 404


def test_speed_recomputes_throughput_from_usage():
    from polytoken.agent.calculations import speed_metrics
    rows = [dict(ok=True, variant=v, ttft_s=.2, latency_s=1.2,
                 usage={'completion_tokens': 100}, output_tokens_per_s=999.)
            for v in ('original', 'changed', 'changed', 'original') * 2]
    assert speed_metrics({'runs': rows})['speed/output_tokens_per_s/original_median'] == 100.


def test_background_jobs_publish_running_then_verified(apparatus):
    a = apparatus
    agent = Investigation(a['tools'], a['memory'], background=True)
    initial = agent.run('samudra')
    assert initial['status'] == 'running'
    assert initial['jobs']['status'] == 'queued'
    assert a['tools'].budget.counts['hosted'] == 0
    assert not any(e['event'] == 'done' for e in agent.events)
    updates = []
    final = agent.finish_jobs('samudra', updates.append)
    assert [r['status'] for r in updates] == ['running', 'complete']
    assert final['id'] == initial['id']
    assert final['dropped_claims'] == []
    assert all(c['verified'] for c in final['claims'])
    values = {c['id']: c['value'] for c in final['claims']}
    assert values['budget/hosted'] == 0
    assert values['jobs/hosted'] == 48
    progress = [e for e in agent.events if e['event'] == 'experiment_progress']
    assert [e['done'] + e['failed'] for e in progress] == list(range(41))
    assert all(e['total'] == 40 for e in progress)
    assert [e['event'] for e in agent.events[-2:]] == ['experiment_done', 'done']


def test_cache_reuses_successful_calls_and_retries_failed_only(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    original = t.generate
    failed_once = []
    def fail_one(prompt, **kwargs):
        if not failed_once:
            failed_once.append(True)
            kwargs['before_attempt']()
            raise RuntimeError('one unavailable response')
        return original(prompt, **kwargs)
    t.generate = fail_one
    first = t.fix_experiment('samudra', 'english_system')
    assert sum(p[v]['ok'] for p in first['pairs'] for v in ('original', 'changed')) == 39
    t.generate = original
    t.budget = BudgetGuard()
    second = t.fix_experiment('samudra', 'english_system')
    assert all(p[v]['ok'] for p in second['pairs'] for v in ('original', 'changed'))
    assert t.budget.counts['hosted'] == 1
    t.budget = BudgetGuard()
    t.fix_experiment('samudra', 'english_system')
    assert t.budget.counts['hosted'] == 0


def test_quality_refuses_nineteen_complete_pairs(apparatus):
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    experiment = t.fix_experiment('samudra', 'english_system')
    experiment['pairs'][0]['changed']['ok'] = False
    before = t.budget.counts['nemotron']
    result = t.quality_judge(experiment['pairs'])
    assert result['sample_status'] == 'insufficient sample'
    assert t.budget.counts['nemotron'] == before
    assert all(p['same_facts'] is None for p in result['pairs'])


def test_prompt_bill_uses_history_and_measured_system_not_generated_lengths(apparatus):
    from polytoken.agent.calculations import baseline_metrics, experiment_metrics
    t = apparatus['tools']
    config, ids = t.load_company('samudra')
    t.measure('samudra', config, ids)
    experiment = t.fix_experiment('samudra', 'english_system')
    original = experiment_metrics(experiment, t.snapshot, t.prices, t.fx)
    baseline = baseline_metrics(t.snapshot, t.prices, t.fx)
    assert original['experiment/original_monthly_inr'] == baseline['baseline/fixture/model/monthly_inr']
    for pair in experiment['pairs']:
        pair['changed']['output_tokens'] *= 100
    changed = experiment_metrics(experiment, t.snapshot, t.prices, t.fx)
    assert changed['experiment/changed_monthly_inr'] == original['experiment/changed_monthly_inr']
    assert changed['experiment/output_tokens_change'] > original['experiment/output_tokens_change']
    experiment['changed_system_tokens'] *= 2
    measured = experiment_metrics(experiment, t.snapshot, t.prices, t.fx)
    assert measured['experiment/changed_monthly_inr'] > changed['experiment/changed_monthly_inr']


@pytest.mark.parametrize('succeed,cap,expected', [(True, 70, 3), (False, 70, 3), (False, 2, 2)])
def test_job_timeout_retries_are_physical_budget_attempts(settings, logger, clock, succeed, cap, expected):
    import httpx
    from polytoken.agent.jobs import JobBudget
    from polytoken.llm import NvidiaGenerator, SlidingWindowLimiter, LLMError
    reasoning = BudgetGuard(clock=clock)
    clock.now = 400  # A completed reasoning deadline does not consume job time.
    guard = JobBudget(reasoning)
    guard.LIMITS = {**guard.LIMITS, 'hosted': cap}
    calls = []
    def handle(request):
        calls.append(request)
        if not succeed or len(calls) < 3:
            raise httpx.ReadTimeout('fixture timeout')
        return httpx.Response(200, json={'choices': [{'message': {'content': 'ok'}}], 'usage': {}})
    with NvidiaGenerator(settings, logger=logger, client=httpx.Client(transport=httpx.MockTransport(handle)),
                         limiter=SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep),
                         clock=clock, sleep=clock.sleep, jitter=lambda: 0) as generator:
        def run():
            return generator.generate('test', max_retries=2, retry_timeouts=True, timeout_s=120,
                                      before_attempt=lambda: guard.consume('hosted'),
                                      remaining=guard.remaining, abort=guard.check)
        if succeed:
            assert run()['text'] == 'ok'
        else:
            with pytest.raises(LLMError):
                run()
    assert len(calls) == guard.counts['hosted'] == expected
    assert all(r.extensions['timeout']['read'] == 120 for r in calls)
    with pytest.raises(BudgetExceeded):
        reasoning.check()


def test_api_serves_running_report_then_same_id_completed():
    import threading
    published, release = threading.Event(), threading.Event()
    def run(company, run_id, event_sink, report_sink, **kwargs):
        report_sink({'id': run_id, 'status': 'running', 'jobs': {'status': 'running'}, 'claims': []})
        published.set()
        release.wait(5)
        final = {'id': run_id, 'status': 'complete', 'claims': []}
        event_sink({'event': 'experiment_done', 'investigation_id': run_id})
        event_sink({'event': 'done', 'investigation_id': run_id})
        return final, []
    with TestClient(create_app(run=run, reference=False)) as client:
        identifier = client.post('/investigations', json={'company': 'samudra'}).json()['id']
        try:
            assert published.wait(2)
            response = client.get(f'/investigations/{identifier}/report')
            assert response.status_code == 202
            assert response.json()['jobs']['status'] == 'running'
        finally:
            release.set()
        events = client.get(f'/investigations/{identifier}/events').text
        assert events.index('event: experiment_done') < events.index('event: done')
        assert client.get(f'/investigations/{identifier}/report').json()['id'] == identifier
        assert client.get(f'/investigations/{identifier}/report').json()['status'] == 'complete'


def test_job_deadline_and_speed_cache(apparatus, clock):
    from polytoken.agent.jobs import JobBudget
    guard = JobBudget(BudgetGuard(clock=clock))
    clock.now += 1800
    with pytest.raises(BudgetExceeded, match='wall'):
        guard.consume('hosted')
    a = apparatus
    agent = Investigation(a['tools'], a['memory'], background=True)
    agent.run('samudra')
    agent.finish_jobs('samudra', lambda _: None)
    a['tools'].budget = BudgetGuard()
    second = Investigation(a['tools'], a['memory'], background=True)
    second.run('samudra')
    report = second.finish_jobs('samudra', lambda _: None)
    assert report['jobs']['budget']['hosted'] == 0
    assert report['speed_status'].startswith('inconclusive; cached')
    assert report['dropped_claims'] == []


def test_completed_job_rechecks_previously_verified_baseline(apparatus):
    a = apparatus
    agent = Investigation(a['tools'], a['memory'], background=True)
    initial = agent.run('samudra')
    assert initial['top_finding']
    raw = next(e for e in a['world'].events() if e['event_id'] == a['tools'].snapshot_id)
    raw['payload']['counts'][0]['tokens'] += 1
    a['world'].db.execute('UPDATE events SET payload=? WHERE event_id=?', (json.dumps(raw['payload']), raw['event_id']))
    final = agent.finish_jobs('samudra', lambda _: None)
    assert final['top_finding'] is None
    assert final['top_fix'] is None
    assert any(c['id'].startswith('baseline/') for c in final['dropped_claims'])
    assert not any(c['id'].startswith('baseline/') for c in final['claims'])


def test_reasoning_usage_does_not_become_visible_output_throughput():
    from polytoken.agent.calculations import speed_metrics
    rows = [dict(ok=True, variant=v, ttft_s=.2, latency_s=1.2,
                 usage={'completion_tokens': 100}, throughput_supported=False)
            for v in ('original', 'changed', 'changed', 'original') * 2]
    metrics = speed_metrics({'runs': rows})
    assert metrics['speed/completed_runs'] == 8
    assert metrics['speed/ttft_s/original_median'] == .2
    assert metrics['speed/latency_s/original_median'] == 1.2
    assert not any('output_tokens_per_s' in key for key in metrics)


def test_offline_throughput_recheck_keeps_raw_report_and_other_claims(apparatus, tmp_path, monkeypatch):
    import importlib.util
    import sys
    from contextlib import contextmanager
    spec = importlib.util.spec_from_file_location('recheck', Path(__file__).resolve().parents[1] / 'scripts/recheck_reasoning_speed.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a = apparatus
    report = Investigation(a['tools'], a['memory']).run('samudra')
    eid = a['tools'].observe('query_result', {'serving_verification': {'fixture/hosted': {'generation_options': {'reasoning_effort': 'low'}}}}, 'fixture catalogue')
    report['evidence_ids'].append(eid)
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report))
    (tmp_path / 'logs/investigations').mkdir(parents=True)
    @contextmanager
    def existing_world(**kwargs):
        yield a['world']
    monkeypatch.setattr(module, 'WorldModel', existing_world)
    monkeypatch.setattr(sys, 'argv', ['recheck', str(path)])
    monkeypatch.chdir(tmp_path)
    before_calls = len(a['generator'].calls)
    module.main()
    revised = json.loads(path.read_text())
    assert revised['id'] == report['id']
    assert len(revised['dropped_claims']) == 9
    assert all(r['id'].startswith('speed/output_tokens_per_s/') for r in revised['dropped_claims'])
    assert all(c['verified'] for c in revised['claims'])
    assert json.loads((tmp_path / 'report_before_throughput_correction.json').read_text()) == report
    assert len(a['generator'].calls) == before_calls
