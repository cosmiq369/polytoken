"""Offline development fixtures built by the production billing projection code."""
import json
from pathlib import Path
import sys

from polytoken.billing_view import archived_events, build_billing, BillingUnavailable
from polytoken.currencies import load_currencies
from polytoken.logs import JsonlLogger
from polytoken.tokens import token_pieces

root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
events=archived_events(root/'logs')
views={}
for path in sorted((root/'logs/sample').rglob('agent_*_report.json')):
    report=json.loads(path.read_text())
    if report['id'] in views:continue
    try:
        view=build_billing(report,events,logger=JsonlLogger(root/'logs',run_id=report['id']))
    except (BillingUnavailable,KeyError,ValueError) as exc:
        view=dict(id=report['id'],status='not measured',reason=str(exc),claims=[])
    target=out/(report['id']+'.json');target.write_text(json.dumps(view,ensure_ascii=False))
    views[report['id']]=str(target)
    if path.name=='agent_samudra_v3_report.json':samudra=view
(out/'index.json').write_text(json.dumps(views))
(out/'currencies.json').write_text(json.dumps(load_currencies()))
strips={}
for text in samudra.get('default_text',{}).values():
    if not isinstance(text,str) or text in ('samudra',''):continue
    if text not in (samudra['default_text']['native'],samudra['default_text']['english']):continue
    for model in samudra.get('models',[]):
        spec=model['tokenizer']
        result=token_pieces(spec,text)
        strips[text+'\n'+spec]=result
(out/'tokens.json').write_text(json.dumps(strips,ensure_ascii=False))
print('Prepared',len(views),'billing views and',len(strips),'local token strips')
