"""Offline evaluation of the dated model-fit addendum; never an agent input."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .billing_view import EventWorld, archived_events
from .checker import Checker
from .logs import JsonlLogger
from .model_fit import replay_fit

EXPECTED = {
    'samudra': ('code_mixed', 'chat', 'meta-llama/Llama-3.1-8B-Instruct'),
    'swara': ('native_script', 'voice', 'google/gemma-3-4b-it'),
    'raitu': ('native_script', 'voice', 'google/gemma-3-4b-it'),
    'paisa': ('code_mixed', 'chat', 'meta-llama/Llama-3.1-8B-Instruct'),
}
LIMITS = {'nemotron':25,'judge':45,'hosted':70,'sql':60}


def latest_complete(reports, records):
    world=EventWorld(records);chosen={}
    for path,report in reports:
        if report.get('status')!='complete' or report.get('company') not in EXPECTED:continue
        budget=next((c for c in report['claims'] if c['id']=='budget/duration_s'),None)
        if not budget:continue
        eid=budget['recompute']['inputs']['budget'];world.verify(eid)
        stamp=datetime.fromisoformat(world.records[eid]['provenance']['fetched_at'].replace('Z','+00:00'))
        key=(stamp,report['id']);company=report['company']
        if company not in chosen or key>chosen[company][0]:chosen[company]=(key,path,report)
    return {c:(p,r) for c,(_,p,r) in chosen.items()}


def evaluate(report, records, logger):
    if report.get('schema_version')!='3':
        # Historical records retain the rubric that was registered for them.
        from .archival_score import evaluate as historical_evaluate
        return historical_evaluate(report,records,logger)
    world=EventWorld(records)
    checked,dropped=Checker(SimpleNamespace(world=world),logger).check(report['claims'])
    if dropped:raise ValueError(f"{report['id']}: {len(dropped)} claims failed evidence replay")
    fit,fit_claims=replay_fit(report,world,logger)
    if fit is None:raise ValueError('Model-fit evidence is incomplete')
    if fit!=report.get('model_fit'):raise ValueError('Saved model-fit decision differs from recomputation')
    values={c['id']:c['value'] for c in checked};company=report['company']
    script,channel,model=EXPECTED[company]
    actual=fit['cost_candidate']['model'] if fit['cost_candidate'] else None
    profile_pass=fit['profile']['dominant_script']==script and fit['profile']['channel']==channel
    # An abstention for unmeasured voice latency is required, not a failed result.
    constraint_pass=(fit['recommendation'] is None if channel=='voice' and all(r['latency']=='unverified' for r in fit['models']) else
                     fit['recommendation'] is not None and fit['recommendation']['latency'] in ('within target','not required'))
    limits={k:dict(actual=values.get('budget/'+k),maximum=v,respected=values.get('budget/'+k,v+1)<=v) for k,v in LIMITS.items()}
    limits['reasoning_seconds']=dict(actual=values.get('budget/duration_s'),maximum=360,respected=values.get('budget/duration_s',361)<=360)
    result=dict(company=company,run_id=report['id'],verified_claims=len(checked),
        top_finding=dict(status='pass' if profile_pass else 'fail',expected_script=script,actual_script=fit['profile']['dominant_script']),
        expected_model=dict(status='pass' if actual==model else 'fail',expected=model,actual=actual),
        constraints=dict(status='pass' if constraint_pass else 'fail',reason=fit['status']),
        profile={k:v for k,v in values.items() if k.startswith('profile/')},
        top_three=[dict(model=r['model'],provider=r['provider'],usd_per_1000=values[r['cost_claim']],token_ratio=values[r['ratio_claim']],claim_ids=[r['cost_claim'],r['ratio_claim']]) for r in fit['models'][:3]],
        recommendation=fit['recommendation'],cost_candidate=fit['cost_candidate'],runner_up=fit['runner_up'],avoid=fit['avoid'],
        limits=limits,quality='verify on your sample',evidence_ids=fit['evidence_ids'])
    logger.write('contract_score','model_fit_evaluated',**result)
    return result


def score(sample_dir='logs/sample', output=None):
    sample=Path(sample_dir);output=Path(output) if output else sample/'model_fit_score'
    records=archived_events(sample.parent)
    reports=[(p,json.loads(p.read_text())) for p in sample.glob('*_report.json')]
    chosen=latest_complete([(p,r) for p,r in reports if r.get('schema_version')=='3'],records)
    logger=JsonlLogger(sample.parent,run_id='offline-model-fit-score');rows=[]
    for company in EXPECTED:
        if company not in chosen:
            rows.append(dict(company=company,status='no complete model-fit run'));continue
        p,r=chosen[company];row=evaluate(r,records,logger)
        row.update(report_file=str(p),report_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            contract_file='docs/CONTRACT.md',contract_sha256=hashlib.sha256(Path('docs/CONTRACT.md').read_bytes()).hexdigest())
        rows.append(row)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    lines=['# Model-fit addendum score','',
        'The scorer recomputes claims and recommendations from authenticated evidence. It is not imported by the agent. Expected winners were registered before data; failures remain visible.','',
        '| Company | Profile prediction | Model prediction | Constraint handling | Candidate |',
        '| --- | --- | --- | --- | --- |']
    for r in rows:
        if 'expected_model' not in r:lines.append(f"| {r['company']} | no complete run | | | |");continue
        lines.append(f"| {r['company']} | {r['top_finding']['status']} | {r['expected_model']['status']} | {r['constraints']['status']} | {r['expected_model']['actual']} |")
        lines.extend(['',f"## {r['company']}",'',f"Report: [{Path(r['report_file']).name}]({Path(r['report_file']).name}). Quality: verify on your sample. {r['constraints']['reason']}.",'',
            '| Model | Provider | USD / 1,000 conversations | Tokens / English |','| --- | --- | ---: | ---: |'])
        for m in r['top_three']:lines.append(f"| {m['model']} | {m['provider']} | {m['usd_per_1000']:.6f} | {m['token_ratio']:.3f}× |")
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    return rows
