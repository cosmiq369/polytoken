"""Offline route and real-browser checks for the no-build interface."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from polytoken.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_ui_mount_and_api_precedence(tmp_path, monkeypatch):
    # The static directory is resolved from the source, not the working directory.
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app(reference=False, state_dir=tmp_path, log_dir=tmp_path)) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'text/html' in page.headers['content-type']
        assert '<title>PolyToken' in page.text
        for filename in ('app.js', 'styles.css'):
            assert client.get('/' + filename).status_code == 200
        assert client.get('/investigations/unknown/report').status_code == 404
        assert client.get('/evidence/unknown').status_code == 404
        assert client.post('/investigations', json={'company': 'unknown'}).status_code == 422
        assert client.get('/.env').status_code == 404
        assert client.get('/src/polytoken/api.py').status_code == 404
        assert client.get('/%2e%2e/.env').status_code == 404


def test_ui_saved_reports_and_browser_flows(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the optional headless UI check')
    env = os.environ.copy()
    # Use an existing Playwright installation; never install npm packages for this UI.
    bundled = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
    if (bundled / 'playwright/package.json').exists():
        env['NODE_PATH'] = os.pathsep.join(filter(None, [env.get('NODE_PATH'), str(bundled)]))
    probe = subprocess.run([node, '-e', "require.resolve('playwright')"], env=env, capture_output=True)
    if probe.returncode:
        pytest.skip('Playwright is not installed; see web/README.md for the schema contract')
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(ROOT / 'src'), env.get('PYTHONPATH')]))
    fixtures = tmp_path / 'browser-fixtures'
    prepare = subprocess.run([sys.executable, str(ROOT / 'web/prepare-ui-fixtures.py'), str(fixtures)],
                             cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    assert prepare.returncode == 0, prepare.stdout + prepare.stderr
    env['UI_BILLING_FIXTURES'] = str(fixtures)
    args = [node, str(ROOT / 'web/check-ui.cjs')]
    if env.get('UI_SCREENSHOTS') == '1':
        args.append('--screenshots')
    result = subprocess.run(args, cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'UI checks passed' in result.stdout
    console = subprocess.run([node, str(ROOT / 'web/check-console.cjs')], cwd=ROOT, env=env,
                             capture_output=True, text=True, timeout=120)
    assert console.returncode == 0, console.stdout + console.stderr
    assert 'Console checks passed' in console.stdout


def test_currency_reference_list_and_legacy_accounting(tmp_path):
    import json
    from polytoken.currencies import load_currencies
    from polytoken.reference import load_fx
    data = load_currencies()
    assert data['base'] == 'USD'
    assert [r['currency'] for r in data['rates']] == ['USD', 'INR']
    assert data['rates'][1]['per_usd'] == 94.9432
    assert load_fx()['inr_per_usd'] == 94.9432
    raw = json.loads((ROOT / 'data/reference/fx.json').read_text())
    for change in ({'verified': False}, {'per_usd': 0}, {'per_usd': float('nan')}, {'currency': 'USD'}, {'as_of': '2026-10-25'}):
        row = {**raw['rates'][0], **change}
        path = tmp_path / 'fx.json'
        path.write_text(json.dumps({'base': 'USD', 'rates': [row]}))
        with pytest.raises((ValueError, KeyError)):
            load_currencies(path)
    row = {**raw['rates'][0], 'currency': 'EUR', 'per_usd': 0.9}
    path.write_text(json.dumps({'base': 'USD', 'rates': [*raw['rates'], row]}))
    assert load_currencies(path)['rates'][-1]['currency'] == 'EUR'


@pytest.fixture
def billing_source(tmp_path):
    import copy
    from polytoken.agent.calculations import baseline_metrics
    from polytoken.checker import make_claims, Checker
    from polytoken.meterless.evidence import EvidenceStore
    from polytoken.meterless.world_model import WorldModel
    from polytoken.logs import JsonlLogger
    logger = JsonlLogger(tmp_path / 'logs')
    world = WorldModel(tmp_path / 'state/world.sqlite', logger=logger)
    source = dict(kind='Test-only SQL fixture', at='2026-10-25T00:00:00Z', fetched_at='2026-10-25T00:00:00Z', query='Test-only paired source rows', time_window={'start': '2026-10-25', 'end': '2026-10-25'})
    items = [dict(company='samudra', chat_id='__system__', turn=0, part='system_prompt', native='స్థిరమైన సూచన', en='System rule', lang='te')]
    for turn in range(1,5):
        items.append(dict(company='samudra', chat_id='chat-1', turn=turn, part='user' if turn%2 else 'assistant', native='తెలుగు వాక్యం', en='English sentence', lang='te'))
    counts = []
    for spec in ('fixture/model','fixture/expensive','fixture/no-price'):
        for item in items:
            for lang in ('te','en'):
                counts.append(dict(company='samudra',chat_id=item['chat_id'],turn=item['turn'],part=item['part'],tokenizer_spec=spec,lang_variant=lang,tokens=2 if lang=='en' else {'system_prompt':10,'user':4,'assistant':3}[item['part']],run_id='test-measurement',fragment_rate=.5 if lang=='te' else 0))
    snapshot=dict(config=dict(company='samudra',language='te',model_in_use='fixture/model',monthly_chats=1000),items=items,counts=counts)
    prices=[dict(model=spec,tokenizer_spec=spec,provider='Test-only quote',input_per_mtok_usd=i,output_per_mtok_usd=o,source_url='https://example.test/price',fetched_at=source['fetched_at'],verified=True) for spec,i,o in [('fixture/model',2,4),('fixture/expensive',20,40)]]
    store=EvidenceStore(world)
    inputs=dict(snapshot=store.add('measurement',snapshot,source=source),prices=store.add('price',{'rows':prices},source=source),fx=store.add('price',{'inr_per_usd':2},source=source))
    metrics=baseline_metrics(snapshot,prices,{'inr_per_usd':2})
    claims,_=Checker(store).check(make_claims(metrics,'baseline',inputs))
    own=metrics['baseline/fixture/model/monthly_inr']
    key='hypotheses/fixture/expensive/switch_monthly_saving_inr'
    claims.extend(Checker(store).check(make_claims({key:own-metrics['baseline/fixture/expensive/monthly_inr']},'hypotheses',inputs))[0])
    report=dict(id='test-billing',company='samudra',status='complete',claims=claims,fixes=[dict(lever='model_switch',tokenizer='fixture/expensive',claim_id=key,status='untested estimate',basis='Test-only quoted scenario')])
    yield dict(world=world,report=report,inputs=inputs,logger=logger,tmp_path=tmp_path,events=copy.deepcopy(world.events()))
    world.close()


def test_billing_arithmetic_and_negative_fix(billing_source):
    from polytoken.billing_view import build_billing
    s=billing_source
    b=build_billing(s['report'],s['events'],logger=s['logger'])
    claims={c['id']:c['value'] for c in b['claims']}
    h=lambda key:claims[b['headline'][key]]
    assert h('monthly_usd') == pytest.approx(.094)
    assert h('per_1000_conversations_usd') == pytest.approx(.094)
    assert h('per_reply_usd') == pytest.approx(.000047)
    assert h('english_monthly_usd') == pytest.approx(.040)
    assert h('language_tax_usd') == pytest.approx(.054)
    assert h('language_tax_percent') == pytest.approx(135)
    assert h('token_multiplier') == pytest.approx(41/16)
    assert h('resend_factor') == 2
    assert h('cacheable_share') == pytest.approx(20/35)
    assert h('lone_byte_share') == .5
    steps=b['staircase']['steps']
    assert [claims[r['fields']['input']] for r in steps] == [14,21]
    assert h('transcript_total_per_conversation') == 24
    assert h('billed_total_per_conversation') == 41
    assert b['models'][-1]['price'] is None
    assert b['fixes'][0]['group'] == 'would_cost_more'
    assert claims[b['fixes'][0]['fields']['saving_usd']] < 0
    assert claims[b['fixes'][0]['fields']['after_monthly_usd']] > h('monthly_usd')
    assert all(c['verified'] and c['evidence_ids'] and c['recompute']['formula'] for c in b['claims'])


def test_billing_tampered_missing_and_forged_evidence(billing_source):
    import copy
    from polytoken.billing_view import build_billing, BillingUnavailable
    s=billing_source
    changed=copy.deepcopy(s['events'])
    next(e for e in changed if e['event_id']==s['inputs']['snapshot'])['payload']['counts'][0]['tokens']=999
    with pytest.raises(BillingUnavailable,match='tampered'):
        build_billing(s['report'],changed,logger=s['logger'])
    with pytest.raises(BillingUnavailable):
        build_billing(s['report'],[],logger=s['logger'])
    report=copy.deepcopy(s['report'])
    key='hypotheses/fixture/expensive/switch_monthly_saving_inr'
    next(c for c in report['claims'] if c['id']==key)['value']=99999
    b=build_billing(report,s['events'],logger=s['logger'])
    assert key not in b['report_money']
    assert b['fixes'][0]['group']=='not_measured'
    assert any(c['id']==key for c in b['dropped_claims'])


def test_display_endpoints_and_local_token_boundaries(billing_source, monkeypatch):
    from polytoken import tokens
    from tokenizers import Tokenizer, models, pre_tokenizers
    s=billing_source
    path=s['tmp_path']/'tokenizer.json'
    tk=Tokenizer(models.WordLevel({'[UNK]':0,'తెలుగు':1,'hello':2},unk_token='[UNK]'))
    tk.pre_tokenizer=pre_tokenizers.Whitespace()
    tk.save(str(path))
    monkeypatch.setattr(tokens,'local_tokenizer_files',lambda:{'fixture/model':str(path),'fixture/unavailable':None})
    app=create_app(reference=False,state_dir=s['tmp_path']/'state',log_dir=s['tmp_path']/'logs')
    app.state.manager.runs[s['report']['id']]={'report':s['report']}
    with TestClient(app) as client:
        assert client.get('/currencies').json()['rates'][1]['per_usd']==94.9432
        assert client.get('/investigations/test-billing/billing').json()['base']=='USD'
        # A cached view must not hide a later mutation under the same declared ID.
        import json
        event=next(e for e in s['events'] if e['event_id']==s['inputs']['snapshot'])
        changed=event['payload'].copy()
        changed['counts']=[{**r,'tokens':999} if i==0 else r for i,r in enumerate(changed['counts'])]
        s['world'].db.execute('UPDATE events SET payload=? WHERE event_id=?',(json.dumps(changed),event['event_id']))
        s['world'].db.commit()
        rejected=client.get('/investigations/test-billing/billing').json()
        assert rejected['status']=='not measured' and 'tampered' in rejected['reason']
        assert client.get('/investigations/missing/billing').status_code==404
        assert client.get('/tokens',params={'text':'hello','tokenizer':'file:/etc/passwd'}).status_code==422
        assert client.get('/tokens',params={'text':'hello','tokenizer':'unknown'}).status_code==422
        assert client.get('/tokens',params={'text':'hello','tokenizer':'fixture/unavailable'}).json()['ok'] is False
        result=client.get('/tokens',params={'text':'  తెలుగు  hello  ','tokenizer':'fixture/model'}).json()
        assert result['ok'] is True
        assert ''.join(p['text'] for p in result['pieces'])=='  తెలుగు  hello  '
        assert result['count']==2 and result['tokens_per_word']==1 and result['lone_byte_share']==0
        assert client.get('/evidence/'+result['evidence_id']).status_code==200
        assert client.get('/tokens',params={'text':'x'*2001,'tokenizer':'fixture/model'}).status_code==422
        assert client.get('/tokens',params={'text':'  ','tokenizer':'fixture/model'}).status_code==422
    assert (s['tmp_path']/'logs/token_strip.jsonl').is_file()


def test_byte_labels_reconstruct_telugu_utf8(tmp_path, monkeypatch):
    from polytoken import tokens
    from tokenizers import Tokenizer, models, pre_tokenizers, decoders
    alphabet = pre_tokenizers.ByteLevel.alphabet()
    tokenizer = Tokenizer(models.BPE(vocab={c: i for i, c in enumerate(alphabet)}, merges=[]))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    path = tmp_path / 'tokenizer.json'
    tokenizer.save(str(path))
    monkeypatch.setattr(tokens, 'local_tokenizer_files', lambda: {'test/bytes': str(path)})
    result = tokens.token_pieces('test/bytes', 'త')
    assert result['count'] == 3
    assert all(p['fragment'] for p in result['pieces'])
    assert ' '.join(p['byte_hex'] for p in result['pieces']) == 'E0 B0 A4'
    assert {p['tokenizer_start'] for p in result['pieces']} == {0}
    assert {p['tokenizer_end'] for p in result['pieces']} == {1}
    assert ''.join(p['text'] for p in result['pieces']) == 'త'
