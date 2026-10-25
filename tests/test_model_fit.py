"""Model-fit regressions use small hand-counted fixtures, never provider calls."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from polytoken.model_fit import calculate_fit,script_mix,replay_fit
from polytoken.checker import Checker,make_claims
from polytoken.agent.planner import Planner
from test_agent import apparatus

@pytest.mark.parametrize('text,language,expected',[
 ('నాకు సహాయం కావాలి','te','native_script'),('Naaku sahaayam kaavaali','te','romanized'),
 ('Na app payment pending undi','te','code_mixed'),('मेरी जानकारी बताइए','hi','native_script'),
 ('UPI payment pending hai','hi','code_mixed'),('12345 !!!','hi','unknown'),
 ('Hello world','te','unknown'),('Use app','te','unknown'),('నా app status ఏంటి?','te','code_mixed'),
])
def test_script_classifier(text,language,expected):
    assert script_mix(text,language)['bucket']==expected


def fixture(channel='chat'):
    config=dict(company='fixture',language='te',model_in_use='one',monthly_chats=1000,latency_target_s=3,
        channel=channel,role='support',dataset_version='model-fit-v1',current_model='A')
    items=[dict(company='fixture',chat_id=c,turn=t,part=p,native=n,en=e,lang='te') for c,t,p,n,e in [
        ('__system__',0,'system_prompt','English policy','English policy'),
        ('chat',1,'user','నాకు సహాయం కావాలి','I need help'),('chat',2,'assistant','వివరాలు చెప్పండి','Give details')]]
    counts=[]
    for spec,native in [('one',[10,30,20]),('two',[10,4,2])]:
        for i,item in enumerate(items):
            for lang,n in [('te',native[i]),('en',[10,3,2][i])]:
                counts.append(dict(company='fixture',chat_id=item['chat_id'],turn=item['turn'],part=item['part'],tokenizer_spec=spec,lang_variant=lang,tokens=n,run_id='measured'))
    prices=[dict(model=m,provider='fixture',tokenizer_spec=spec,input_per_mtok_usd=ip,output_per_mtok_usd=op,
        verified=True,source_url='https://example.test/price',fetched_at='2026-10-25T00:00:00Z') for m,spec,ip,op in [('A','one',1,1),('B','two',2,2),('C','one',2,1)]]
    return dict(config=config,items=items,counts=counts),prices


def test_ranking_uses_own_tokenizer_counts_and_every_model():
    snap,prices=fixture();metrics,fit=calculate_fit(snap,prices)
    assert [r['model'] for r in fit['models']]==['B','A','C']
    assert [metrics[r['cost_claim']] for r in fit['models']]==pytest.approx([.032,.060,.1])
    assert [metrics[r['ratio_claim']] for r in fit['models']]==pytest.approx([16/15,60/15,60/15])
    assert fit['recommendation']['model']=='B' and fit['runner_up']['model']=='A'
    assert fit['avoid']['model']=='A' # highest penalty among cheap quotes, not most expensive C
    assert metrics['profile/conversations']==1 and metrics['profile/answer_billed_share']==1/3
    assert all(r['quality']=='verify on your sample' for r in fit['models'])


def test_unpriced_families_and_missing_prices_are_not_zero_filled():
    snap,prices=fixture();metrics,fit=calculate_fit(snap,[prices[0]])
    assert fit['tokenizer_fit_only'][0]['tokenizer']=='two'
    assert metrics[fit['tokenizer_fit_only'][0]['ratio_claim']]==16/15
    _,missing=calculate_fit(snap,[])
    assert missing['recommendation'] is None and missing['models']==[]
    assert len(missing['tokenizer_fit_only'])==2


def timings(snap,model,seconds,**kwargs):
    return dict(runs=[dict(request_id=f'call-{i}',ok=True,finish_reason='stop',model=model,provider='fixture',company='fixture',
        dataset_version='model-fit-v1',measurement_run_ids=['measured'],latency_s=seconds,
        source='fixture stream',query='fixture generation',fetched_at='2026-10-25T00:00:00Z',
        time_window={'start':'2026-10-25T00:00:00Z','end':'2026-10-25T00:00:01Z'},**kwargs) for i in range(4)])


def test_voice_requires_matching_complete_latency_sample():
    snap,prices=fixture('voice')
    _,fit=calculate_fit(snap,prices)
    assert fit['recommendation'] is None and fit['cost_candidate']['model']=='B'
    _,fit=calculate_fit(snap,prices,timings(snap,'A',2))
    assert fit['recommendation']['model']=='A' # cheaper B lacks evidence
    repeated=timings(snap,'B',2)
    for r in repeated['runs']:r['request_id']='same-call'
    assert calculate_fit(snap,prices,repeated)[1]['recommendation'] is None
    _,fit=calculate_fit(snap,prices,timings(snap,'B',4))
    assert fit['recommendation'] is None
    for change in [{'model':'stand-in'},{'provider':'different'},{'cache_hit':True},{'measurement_run_ids':['older']},{'company':'another'},{'finish_reason':'length'}]:
        timing=timings(snap,'B',2)
        for r in timing['runs']:r.update(change)
        _,fit=calculate_fit(snap,prices,timing)
        assert fit['recommendation'] is None


def test_alternate_provider_can_meet_latency_even_if_cheapest_provider_cannot():
    snap,prices=fixture('voice');extra={**prices[1],'provider':'second','input_per_mtok_usd':3}
    t=timings(snap,'B',2)
    for r in t['runs']:r['provider']='second'
    _,fit=calculate_fit(snap,prices+[extra],t)
    assert fit['recommendation']['provider']=='second'


def test_checker_drops_tampered_fit_and_replay_rebuilds_labels(apparatus):
    t=apparatus['tools'];snap,prices=fixture()
    sid=t.observe('measurement',snap,'fixture source');pid=t.observe('price',{'rows':prices},'fixture quote');tid=t.observe('measurement',{'runs':[]},'fixture timing')
    inputs=dict(snapshot=sid,prices=pid,timings=tid)
    metrics,fit=calculate_fit(snap,prices)
    claims=make_claims(metrics,'model_fit',inputs);checked,dropped=Checker(t.store).check(claims)
    assert not dropped
    fake=copy.deepcopy(claims);fake[0]['value']=99
    assert Checker(t.store).check(fake)[1]
    from polytoken.billing_view import EventWorld
    report=dict(company='fixture',claims=checked,model_fit={'recommendation':'forged'})
    replayed,_=replay_fit(report,EventWorld(t.store.world.events()))
    assert replayed['recommendation']['model']=='B'
    report['claims'].pop()
    assert replay_fit(report,EventWorld(t.store.world.events()))==(None,[])


def test_active_product_has_no_withdrawn_lever():
    root=Path(__file__).resolve().parents[1]
    paths=[p for p in (root/'src/polytoken').glob('*.py') if not p.name.startswith('archival_')]+list((root/'src/polytoken/agent').glob('*.py'))+list((root/'web').glob('*.js'))+[root/'src/polytoken/tools/__init__.py',root/'README.md',root/'docs/SUBMISSION.md']
    for p in paths:
        assert 'english_system' not in p.read_text(),p
        assert 'Keep system instructions in English' not in p.read_text(),p


def test_planner_cannot_skip_checker_with_early_done(logger):
    calls=[]
    def generate(prompt):
        calls.append(prompt)
        return {'text':json.dumps(dict(why='Finish using evidence',tool='judge',args={},done=True))}
    fallback=dict(why='Record missing sample',tool='judge',args={},done=False)
    assert Planner(generate,logger).plan('judge',{},fallback,{'judge':[{}]})==fallback
    assert len(calls)==2


def test_derived_costs_have_checked_dependencies_and_missing_best_cost():
    snap,prices=fixture();metrics,fit=calculate_fit(snap,prices)
    assert fit['lowest_unit_price']['model']=='A'
    best=fit['models'][0]
    for row in fit['provider_quotes']:
        assert row['monthly_usd']==pytest.approx(metrics[row['cost_claim']]*metrics['profile/monthly_conversations']/1000)
        assert row['cost_multiple']==pytest.approx(metrics[row['cost_claim']]/metrics[best['cost_claim']])
        assert row['multiple_claim_ids']==[row['cost_claim'],best['cost_claim']]
        assert row['monthly_claim_ids']==[row['cost_claim'],'profile/monthly_conversations']
    zero=[{**p,'input_per_mtok_usd':0,'output_per_mtok_usd':0} for p in prices]
    assert all(r['cost_multiple'] is None for r in calculate_fit(snap,zero)[1]['models'])


@pytest.mark.parametrize('company',['samudra','swara','raitu','paisa'])
def test_saved_avoid_uses_highest_penalty_among_cheap_models(company):
    from polytoken.billing_view import EventWorld,archived_events
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/f'logs/sample/agent_{company}_model_fit_report.json').read_text())
    world=EventWorld(archived_events(root/'logs'))
    fit,claims=replay_fit(report,world)
    assert fit is not None
    values={c['id']:c['value'] for c in claims}
    inputs=claims[0]['recompute']['inputs']
    prices=world.verify(inputs['prices'])['rows']
    from polytoken.model_fit import quote_key
    quotes={quote_key(p):p for p in prices}
    order=sorted(fit['models'],key=lambda r:(quotes[r['key']]['input_per_mtok_usd']+quotes[r['key']]['output_per_mtok_usd'],r['model'],r['provider']))
    cheap=order[:(len(order)+1)//2]
    candidates=[r for r in cheap if r['model']!=fit['cost_candidate']['model'] and values[r['ratio_claim']]>1 and values[r['cost_claim']]>values[fit['cost_candidate']['cost_claim']]]
    assert fit['avoid']['model']==max(candidates,key=lambda r:values[r['ratio_claim']])['model']
    assert 'tokenizer penalty' in fit['avoid']['reason']


def test_fit_fields_survive_secret_redaction(logger):
    snap,prices=fixture()
    _,fit=calculate_fit(snap,prices)
    assert logger.redact(fit)['lowest_unit_price']==fit['lowest_unit_price']
    assert logger.redact(fit)['avoid']==fit['avoid']
