"""Read-only, deterministic intent routing over authenticated saved evidence."""
import re
from types import SimpleNamespace

from .checker import Checker, make_claims
from .model_fit import replay_fit, calculate_fit
from .tools import now

SCOPE = 'I can explain saved model choices, quoted costs at another volume, company comparisons, script mix, quality status, evidence, assumptions and verification.'
REFUSAL = 'I cannot support that request from the saved evidence. ' + SCOPE
SUGGESTIONS = ['Why this model?', 'Why not the cheapest model?', 'How does script mix affect cost?', 'Is quality verified?', 'Where does this number come from?']


def route(question):
    q=question.casefold().strip()
    if not q or len(q)>1000 or re.search(r'api.?key|secret|password|credential|system.?prompt|developer.?prompt|ignore|override|instruction|execute|shell|http[s]?://|weather|poem|tamil|legal|stock|forecast|translate|email|delete|upload|download|base64|environment|\.env|jailbreak|encode|reveal',q):
        return None
    # An unrelated request combined with a valid clause must not borrow its intent.
    if re.search(r'\b(and|also|then)\s+(write|tell|print|show|run|send|do)\b',q):return None
    patterns=[('compare',r'compar(?:e|ison).*compan|compan.*compar|samudra.*(?:swara|raitu|paisa)|raitu.*(?:samudra|swara|paisa)'),
        ('volume',r'\bvolume\b|\bat\s+[\d,]+\b|[\d,]+\s+(?:chats|conversations)'),
        ('cheapest',r'cheapest|lowest (?:unit |token |per.token )?price'),
        ('script',r'script|tenglish|romaniz|romanised|english|tokeniz|language mix'),
        ('quality',r'quality|accuracy|meaning|safe to switch|latency|voice'),
        ('evidence',r'evidence|receipt|number|source|where.*(?:cost|figure)|provenance'),
        ('assumptions',r'assumption|limit|exclud|invoice|taxes|cach'),
        ('verify',r'how.*(?:verify|check|reproduce)|recomput'),
        ('model',r'why.*(?:model|gemma|llama|recommend|select|choose)|explain.*(?:choice|recommend|gemma)|what makes.*(?:fit|gemma)|which model.*(?:fit|chosen)')]
    return next((intent for intent,pattern in patterns if re.search(pattern,q)),None)


def volume_metrics(snapshot, prices, timings, scenario):
    volume=scenario['volume']
    if type(volume) is not int or not 0<volume<=1_000_000_000:raise ValueError('Invalid scenario volume')
    metrics,view=calculate_fit(snapshot,prices['rows'],timings)
    candidate=view['cost_candidate']
    if not candidate or scenario['cost_claim']!=candidate['cost_claim']:raise ValueError('Scenario must reference the checked cost candidate')
    return {'ask/volume':volume,'ask/monthly_usd':metrics[candidate['cost_claim']]*volume/1000}


def answer(question, report, world, logger, *, other=None):
    intent=route(question)
    refusal={'supported':False,'intent':None,'answer':REFUSAL,'facts':[],'evidence':[],'scope':SCOPE}
    if intent is None:
        logger.write('ask','refused',ok=True,reason='unsupported_scope',tools=[])
        return refusal
    fit,claims=replay_fit(report,world,logger)
    if not fit:return refusal
    # A question cannot silently use another company's evidence.
    names={'samudra':'samudra','swara':'swara','raitu':'raitu','paisa':'paisa'}
    mentioned={value for key,value in names.items() if key in question.casefold()}
    if intent!='compare' and mentioned and mentioned!={report['company']}:return refusal
    by_id={c['id']:c for c in claims};facts=[]
    def fact(label,identifier,source=None,run=None):
        claim=(source or by_id).get(identifier)
        if claim:
            facts.append({'label':label,'claim':claim,'run_id':run or report['id']})
    best=fit.get('cost_candidate');cheap=fit.get('lowest_unit_price')
    # Model identifiers may contain digits; quantitative assertions live only in facts.
    model=best['model'] if best else 'unavailable'
    if intent=='model':
        text=f'The quoted content-cost candidate is {model}. It has the lowest reconstructed content cost for this stored workload. This does not establish better quality. Voice latency must be verified on the exact model and provider.'
        if best:
            fact('Candidate USD per thousand conversations',best['cost_claim']);fact('Candidate billed tokens / English',best['ratio_claim'])
    elif intent=='cheapest':
        if not best or not cheap:return refusal
        text=('The lowest unit-price model also has the lowest measured content cost.' if best['model']==cheap['model'] else
              'The lowest unit-price model costs more for this workload because unit prices alone do not account for its tokenizer and the amount of replayed history.')
        text+=f" Content-cost candidate: {best['model']}. Lowest equal-basket unit price: {cheap['model']}. Quality remains unverified."
        fact('Candidate USD per thousand conversations',best['cost_claim']);fact('Lowest unit-price model USD per thousand conversations',cheap['cost_claim']);fact('Lowest unit-price model billed tokens / English',cheap['ratio_claim'])
    elif intent=='volume':
        values=re.findall(r'(?<![\w.])[\d][\d,]*(?![\w.])',question)
        if len(values)!=1:return refusal
        raw=values[0]
        if not re.fullmatch(r'\d+|\d{1,3}(?:,\d{3})+',raw):return refusal
        volume=int(raw.replace(',',''))
        if not 0<volume<=1_000_000_000 or not best:return refusal
        # The user's assumption is an explicit evidence input, never a measurement.
        inputs=dict(claims[0]['recompute']['inputs']);stamp=now()
        scenario={'volume':volume,'cost_claim':best['cost_claim'],'supports':list(inputs.values())}
        eid=world.derive(scenario,{'kind':'User scenario assumption','source':'Ask the evidence',
            'query':'Hypothetical monthly conversation volume','fetched_at':stamp,'at':stamp,
            'time_window':{'start':stamp,'end':stamp}},'ask-volume')
        inputs['scenario']=eid
        args={k:world.verify(v) for k,v in inputs.items()}
        candidate=make_claims(volume_metrics(**args),'ask_volume',inputs)
        checked,dropped=Checker(SimpleNamespace(world=world),logger).check(candidate)
        if dropped:return refusal
        for c in checked:fact('Hypothetical monthly USD' if c['id'].endswith('usd') else 'Assumed monthly conversations',c['id'],{c['id']:c})
        logger.write('ask','scenario_evidence',world_event=world.records[eid],ok=True)
        text=f'What-if scenario using the recorded workload and dated quote for {model}. This scales content cost linearly; it is not a new measurement or invoice.'
    elif intent=='compare':
        if not other or other.get('id')==report.get('id'):return refusal
        other_fit,other_claims=replay_fit(other,world,logger)
        if not best or not other_fit or not other_fit.get('cost_candidate'):return refusal
        if mentioned and not mentioned <= {report['company'],other['company']}:return refusal
        text='These are different stored workloads. The normalized content-cost rates can be compared; they do not establish relative quality. Native review and exact voice latency remain unverified.'
        fact(report['company']+' candidate USD per thousand conversations',best['cost_claim'])
        other_best=other_fit['cost_candidate'];fact(other['company']+' candidate USD per thousand conversations',other_best['cost_claim'],{c['id']:c for c in other_claims},other['id'])
    elif intent=='script':
        text='Script mix changes tokenization. These are measured shares of the stored user turns and the candidate’s ratio to paired English. They do not measure the effect of rewriting a new sentence; use the token strip for that comparison.'
        for key in ('native_script','romanized','code_mixed','unknown'):fact(key.replace('_',' ')+' share','profile/'+key+'_share')
        if best:fact('Candidate billed tokens / English',best['ratio_claim'])
    elif intent=='quality':
        text='Quality: verify on your sample. Cost ranking does not establish semantic equivalence. Exact-model/provider/workload voice latency is unverified unless the checked timing evidence says otherwise.'
        for row in fit['models']:
            if row.get('latency_claim'):fact(row['model']+' maximum full-reply seconds',row['latency_claim'])
    elif intent=='evidence':
        text='Each receipt identifies the stored source, query, fetch time and time window, plus the recomputation inputs. Open a fact below to inspect its authenticated evidence. Unchecked numbers are withheld.'
        if best:fact('Candidate USD per thousand conversations',best['cost_claim']);fact('Candidate billed tokens / English',best['ratio_claim'])
    elif intent=='assumptions':
        text='This is a dated content-token estimate from paired conversations, including completed history replay. It excludes provider chat templates, retries, taxes and unpublished cache discounts. Native equivalence, quality and unmeasured latency remain pending. It is not an invoice.'
    else:
        text='Open a receipt, inspect its source SQL and fetch window, then replay its deterministic recipe against the authenticated World Model inputs. Re-run measurements for changed text or prices. Independently review native meaning and test the exact model/provider before switching.'
    wanted={eid for f in facts for eid in f['claim']['evidence_ids']}
    pending=list(wanted)
    while pending:
        for parent in world.records[pending.pop()]['payload'].get('supports',[]):
            if parent not in wanted:wanted.add(parent);pending.append(parent)
    result={'supported':True,'intent':intent,'answer':text,'facts':facts,
            'evidence':[world.records[k] for k in sorted(wanted)],'scope':SCOPE}
    logger.write('ask','answered',ok=True,intent=intent,tools=['read_saved_report','read_world_model','check_claims'],
                 claims=[{'run_id':f['run_id'],'id':f['claim']['id'],'evidence_ids':f['claim']['evidence_ids']} for f in facts])
    return logger.redact(result)
