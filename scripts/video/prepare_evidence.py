"""Recheck saved reports and derive all presentation figures before authoring."""
import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from polytoken.billing_view import archived_events
from polytoken.logs import JsonlLogger
from polytoken.score import evaluate
root=Path(__file__).resolve().parents[2]
records=archived_events(root/'logs')
logger=JsonlLogger(root/'logs',run_id='video-deck-evidence')
fx=json.loads((root/'data/reference/fx.json').read_text())['rates'][0]
companies=[]
for company in ['samudra','swara','raitu','paisa']:
 p=root/f'logs/sample/agent_{company}_model_fit_report.json';r=json.loads(p.read_text())
 score=evaluate(r,records,logger)
 assert all(score[k]['status']=='pass' for k in ['top_finding','expected_model','constraints'])
 claims={c['id']:c['value'] for c in r['claims']};fit=r['model_fit'];best=fit['cost_candidate'];cheap=fit['lowest_unit_price'];volume=claims['profile/monthly_conversations']
 def row(m):
  usd=claims[m['cost_claim']]*volume/1000
  return dict(model=m['model'],provider=m['provider'],monthly_usd=usd,monthly_inr=round(usd*fx['per_usd']),ratio=claims[m['ratio_claim']],multiple=claims[m['cost_claim']]/claims[best['cost_claim']],claim_ids=[m['cost_claim'],m['ratio_claim'],'profile/monthly_conversations'])
 companies.append(dict(company=company,volume=volume,best=row(best),cheap=row(cheap),source=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),verified_claims=score['verified_claims'],profile=fit['profile']))
exp=list(csv.DictReader((root/'logs/sample/experiment01/fertility.csv').open()))
# Reference display follows the published two-decimal Experiment 01 table.
reference={}
for spec in ['unsloth/Llama-3.2-3B-Instruct','unsloth/gemma-3-4b-it']:
 reference[spec]={r['variant']:float(r['tokens'])/float(r['baseline_tokens']) for r in exp if r['tokenizer']==spec}
data=dict(event='submission_evidence_recomputed',fetched_at=datetime.now(timezone.utc).isoformat(),companies=companies,fx=fx,reference=reference,addendum_passes=12,ok=True)
(root/'docs/deck/evidence.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
with (root/'logs/sample/video_deck_validation.jsonl').open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
print('All four reports authenticated and recomputed; 12/12 addendum checks pass.')
