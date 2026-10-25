import copy
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from polytoken.api import create_app
from polytoken.launcher import Launch, parse_sample, priced_models

ROOT=Path(__file__).resolve().parents[1]


def launch_payload(**overrides):
    return dict(name='Test workload',industry='Support',channel='chat',language='te',monthly_chats=200000,
                currency='INR',candidate_models=priced_models(),sample='samudra',**overrides)


@pytest.mark.parametrize('change',[
    {'monthly_chats':0},{'monthly_chats':True},{'name':' '},{'candidate_models':[]},
    {'candidate_models':['unpriced/model']},{'language':'hi'},{'sample':None},
    {'sample':'unknown'},{'currency':'EUR'},{'channel':'email'},
    {'content':'{}','filename':'a.jsonl'},{'latency_target_s':float('inf')},
])
def test_launcher_rejects_bad_workload(change):
    with pytest.raises(ValidationError):Launch.model_validate({**launch_payload(),**change})


def test_jsonl_csv_and_language_bounds():
    text=(ROOT/'web/sample-template.jsonl').read_text();rows=parse_sample('x.jsonl',text,'te')
    import csv,io
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    assert parse_sample('x.csv',out.getvalue(),'te')==rows
    for edited in ([rows[0]], [rows[0],rows[0]], [{**rows[0],'text_en':''},rows[1]], [{**rows[0],'role':'assistant'},rows[1]], [{**rows[0],'lang':'hi'},rows[1]], [{**rows[0],'text_native':'हिन्दी'},rows[1]]):
        with pytest.raises(ValueError):parse_sample('x.jsonl','\n'.join(json.dumps(r) for r in edited),'te')
    for name,value in [('x.txt',text),('x.jsonl','['),('x.csv','chat_id,chat_id\na,b'),('x.jsonl','x'*1_048_577)]:
        with pytest.raises(ValueError):parse_sample(name,value,'te')


def test_demo_launch_uses_sse_and_blocks_upload(tmp_path):
    calls=[]
    def forbidden(**kwargs):calls.append(kwargs);raise AssertionError('Live must not run')
    with TestClient(create_app(run=forbidden,reference=False,demo=True,log_dir=ROOT/'logs',state_dir=tmp_path)) as c:
        payload=launch_payload();payload['monthly_chats']=999
        response=c.post('/investigations',json={'company':'new','launch':payload})
        assert response.status_code==202,response.text
        result=response.json();assert result['mode']=='replay' and result['label']=='Replay of a saved run'
        events=c.get(f"/investigations/{result['id']}/events")
        assert 'event: tool_called' in events.text and 'event: done' in events.text
        report=c.get(f"/investigations/{result['id']}/report").json()
        assert next(x['value'] for x in report['claims'] if x['id']=='profile/monthly_conversations')==200000
        replay=c.get(f"/investigations/{result['id']}/replay").json();assert replay['report']['claims']
        payload.update(sample=None,filename='test.jsonl',content=(ROOT/'web/sample-template.jsonl').read_text())
        blocked=c.post('/investigations',json={'company':'new','launch':payload})
        assert blocked.status_code==409 and 'Live mode needed' in blocked.text
        assert calls==[]


def test_upload_endpoint_forwards_validated_data_and_errors_do_not_echo(tmp_path):
    observed=[]
    def run(company,*,launch,run_id,event_sink):
        observed.append(launch)
        event_sink(dict(event='done',timestamp='2026-10-25T00:00:00Z',investigation_id=run_id,step='report',status='complete'))
        return dict(id=run_id,company=company,status='complete',claims=[]),[]
    with TestClient(create_app(run=run,reference=False,log_dir=tmp_path,state_dir=tmp_path)) as c:
        payload=launch_payload();payload.update(sample=None,filename='test.jsonl',content=(ROOT/'web/sample-template.jsonl').read_text())
        result=c.post('/investigations',json={'company':'new','launch':payload}).json()
        c.get(f"/investigations/{result['id']}/events")
        assert observed[0]['content']==payload['content']
        response=c.post('/investigations',json={'company':'new','launch':{**payload,'content':'PRIVATE-SENTINEL'}})
        assert response.status_code==422 and 'PRIVATE-SENTINEL' not in response.text
        assert c.post('/investigations',content='x'*2_097_153).status_code==413


def test_ingestion_to_real_agent_with_fake_sql_generator(tmp_path,settings,monkeypatch):
    """Exercise import, registrations, measured rows, runtime, checker and SSE.

    Only external services and tokenizer encodings are fakes. No canned report.
    """
    from dataclasses import replace
    from contextlib import nullcontext
    from polytoken import company_db,measure,tokens,config,llm,zetaris
    from polytoken.agent import runtime
    settings=replace(settings,company_db_user='fixture',company_db_password='fixture')
    stored={};writes=[];queries=[]
    class DB:
        def execute(self,sql,*args):writes.append(sql)
    monkeypatch.setattr(company_db,'connect',lambda settings:nullcontext(DB()))
    def upsert(db,table,fields,keys,rows):stored[table]=copy.deepcopy(rows)
    monkeypatch.setattr(company_db,'upsert',upsert)
    def write_batch(settings,rows,batch):stored.setdefault('counts',[]).extend(copy.deepcopy(rows))
    monkeypatch.setattr(measure,'write_batch',write_batch)
    specs={p['tokenizer_spec'] for p in __import__('polytoken.prices',fromlist=['load_prices']).load_prices(ROOT/'data/reference/prices.json') if p['model'] in priced_models()}
    monkeypatch.setattr(tokens,'local_tokenizer_files',lambda:{s:'/test/'+s for s in specs})
    monkeypatch.setattr(tokens,'_tokenizer',lambda s:object())
    monkeypatch.setattr(tokens,'count',lambda s,t:len(t.split())+2)
    monkeypatch.setattr(tokens,'fragment_rate',lambda s,t:0.)
    class SQL:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,q):writes.append(q)
        def query(self,q,**kw):
            queries.append(q)
            if kw.get('before_attempt'):kw['before_attempt']()
            if 'latest_token_counts' in q:return stored['counts']
            if 'polytoken_reference.prices' in q:
                from polytoken.prices import load_prices
                return load_prices(ROOT/'data/reference/prices.json')
            table='bot_config' if '__bot_config' in q else 'chats'
            return next(v for k,v in stored.items() if k.endswith('.'+table))
    class Generate:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def generate(self,prompt,**kw):
            kw['before_attempt']()
            context=json.loads(prompt.split('\n',1)[1].split('\nRepair:')[0]);step=context['step']
            return {'text':json.dumps({'why':'Rank expected cost savings using checked evidence.','tool':step,'args':context['allowed'][step][0],'done':step=='report'}),'usage':{'prompt_tokens':100,'completion_tokens':20}}
    monkeypatch.setattr(runtime,'load_settings',lambda p:settings)
    monkeypatch.setattr(runtime,'ZetarisClient',SQL);monkeypatch.setattr(runtime,'NvidiaGenerator',Generate)
    monkeypatch.setattr(runtime,'discover_hosted',lambda *args:{'families':{}})
    from functools import partial
    run=partial(runtime.investigate,log_dir=tmp_path/'logs',state_dir=tmp_path/'state')
    with TestClient(create_app(run=run,reference=False,log_dir=tmp_path/'logs',state_dir=tmp_path/'state')) as c:
        payload=launch_payload();payload.update(sample=None,filename='test.jsonl',content=(ROOT/'web/sample-template.jsonl').read_text())
        response=c.post('/investigations',json={'company':'new','launch':payload});assert response.status_code==202,response.text
        identifier=response.json()['id'];events=c.get(f'/investigations/{identifier}/events')
        report=c.get(f'/investigations/{identifier}/report').json()
        assert report['status']=='complete',report
        assert report['claims'] and all(c['verified'] for c in report['claims'])
        assert 'event: sql_started' in events.text
        assert any('REGISTER DATASOURCE' in q for q in writes)
        assert all(not q.startswith(('DELETE FROM samudra', 'UPDATE samudra', 'DROP ')) for q in writes)
        assert report['company'].startswith('upload_')
        assert report['model_fit']['models']
        assert any('__chats' in q for q in queries) and any('latest_token_counts' in q for q in queries)
        assert (tmp_path/'logs/launcher.jsonl').exists()
