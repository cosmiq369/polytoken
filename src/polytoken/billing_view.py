"""Read-only billing projections from authenticated World Model evidence.

The existing Checker validates source baselines (including an explicitly derived
English selector); billed_tokens and cost_usd independently reconcile the USD
amounts. This module never changes agent reports or broadens its checker allowlist.
"""
from collections import defaultdict
import copy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

from .agent.calculations import baseline_metrics, select_price
from .checker import Checker, make_claims
from .logs import JsonlLogger
from .measurement_report import billed_tokens
from .meterless.world_model import WorldModel
from .prices import cost_usd


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


class BillingUnavailable(ValueError):
    pass


class EventWorld:
    """Checker-compatible immutable source view, with content-addressed derivations."""
    _provenance = staticmethod(WorldModel._provenance)

    def __init__(self, events):
        self.records = {e['event_id']: e for e in events}
        self.derived = []

    def events(self, kind=None):
        return [e for e in self.records.values() if kind is None or e['kind'] == kind]

    def verify(self, identifier, visiting=None):
        visiting = set() if visiting is None else visiting
        if identifier in visiting:
            raise BillingUnavailable('Cyclic evidence support')
        try:
            e = self.records[identifier]
            digest = hashlib.sha256(f"{e['kind']}|{e['item_key']}|{_canonical(e['payload'])}|{_canonical(e['provenance'])}".encode()).hexdigest()[:24]
            if identifier != 'evt_' + digest:
                raise BillingUnavailable('Stored evidence was tampered with')
            self._provenance(e['provenance'], strict=True)
            for parent in e['payload'].get('supports', []):
                self.verify(parent, visiting | {identifier})
            return e['payload']
        except (KeyError, TypeError, ValueError) as exc:
            raise BillingUnavailable(str(exc)) from exc

    def derive(self, payload, source, key):
        event = dict(kind='measurement', item_key=key, payload=payload, provenance=source)
        digest = hashlib.sha256(f"measurement|{key}|{_canonical(payload)}|{_canonical(source)}".encode()).hexdigest()[:24]
        event['event_id'] = 'evt_' + digest
        self.records[event['event_id']] = event
        self.derived.append(event)
        return event['event_id']


def archived_events(log_dir):
    """Archived rows are recorded SQL evidence, never substitute company fixtures."""
    records = {}
    for path in sorted((Path(log_dir) / 'sample').glob('*world_events.jsonl*')):
        import gzip
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as handle:
            lines = handle.readlines()
        for line in lines:
            row = json.loads(line)
            e = row.get('world_event', row)
            if 'event_id' in e:
                records[e['event_id']] = e
    return list(records.values())


def find_report(identifier, manager, log_dir):
    if not isinstance(identifier, str) or not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-' for c in identifier):
        raise FileNotFoundError('Investigation not found')
    with manager.lock:
        if identifier in manager.runs:
            report = manager.runs[identifier]['report']
            if report is None:
                return None
            return copy.deepcopy(report)
    path = Path(log_dir) / 'investigations' / (identifier + '.json')
    if path.is_file():
        return json.loads(path.read_text())
    for path in sorted((Path(log_dir) / 'sample').glob('*_report.json')):
        row = json.loads(path.read_text())
        if row.get('id') == identifier:
            return row
    raise FileNotFoundError('Investigation not found')


def _source_ids(report):
    recipes = [c['recompute']['inputs'] for c in report.get('claims', [])
               if c.get('verified') is True and c.get('recompute', {}).get('operation') == 'baseline'
               and set(c['recompute'].get('inputs', {})) == {'snapshot', 'prices', 'fx'}]
    if not recipes:
        raise BillingUnavailable('No checked billing snapshot is available in this report.')
    if any(r != recipes[0] for r in recipes):
        raise BillingUnavailable('Mixed billing snapshots cannot support one bill.')
    return recipes[0]


def _usd(row, price):
    return float(cost_usd(price, int(row['billed_input']), int(row['billed_output'])))


def _calculate(snapshot, price_rows, native, english, baseline, fx):
    """Calculation pass. Results are checked again from the authenticated inputs."""
    metrics, models, staircase = {}, [], []
    config, items, counts = snapshot['config'], snapshot['items'], snapshot['counts']
    language, volume = config['language'], int(config['monthly_chats'])
    if volume <= 0:
        raise BillingUnavailable('Monthly volume must be positive')
    def put(spec, field, value, unit, formula):
        key = f'billing/{spec}/{field}'
        if type(value) not in (int, float) or not math.isfinite(value):
            raise BillingUnavailable('Non-finite billing metric')
        metrics[key] = dict(value=value, unit=unit, formula=formula)
        return key
    for spec, n in native.items():
        e = english[spec]
        prefix = f'baseline/{spec}/'
        price = select_price(price_rows, spec)
        row = dict(tokenizer=spec, price=price, fields={}, composition={})
        out = row['fields']
        def add(field, value, unit='number', formula='Recorded source value'):
            out[field] = put(spec, field, value, unit, formula)
            return out[field]
        add('monthly_chats', volume, 'integer', 'Configured monthly conversations')
        add('chat_count', n['chat_count'], 'integer', 'Distinct source chat IDs')
        add('requests', n['requests'], 'integer', 'Completed assistant replies in source chats')
        add('resend_factor', n['requests']/n['chat_count'], 'ratio', 'Completed replies / distinct source conversations')
        add('cacheable_share', n['billed_system_input']/n['billed_input'], 'ratio', 'Identical system prefix tokens across requests / all billed input tokens; eligibility only, no provider discount assumed')
        add('token_multiplier', (n['billed_input']+n['billed_output'])/(e['billed_input']+e['billed_output']), 'ratio', 'Native billed input + output / the same content in measured English tokens')
        for convention in ('billed', 'transcript'):
            if convention == 'billed':
                parts = {part: baseline[prefix+part+'_tokens'] for part in ('system_prompt','user','assistant','output')}
            else:
                parts = dict(system_prompt=n['corpus_system_input'], user=n['corpus_input']-n['corpus_system_input'], assistant=0, output=n['corpus_output'])
            total = sum(parts.values())
            row['composition'][convention] = []
            for part, value in parts.items():
                row['composition'][convention].append(dict(part=part,
                    tokens=put(spec,f'{convention}/{part}/tokens_per_conversation',value/n['chat_count'],'tokens','Component tokens / source conversations'),
                    share=put(spec,f'{convention}/{part}/share',value/total,'ratio','Component tokens / all tokens under this accounting convention')))
            add(convention+'_total_per_conversation', total/n['chat_count'], 'tokens', 'All content tokens under this convention / conversations')
        # Coverage is a token-weighted share of unique measured text items, prompt once.
        measurements = [r for r in counts if r['tokenizer_spec']==spec and r['lang_variant']==language]
        try:
            rates = [float(r['fragment_rate']) for r in measurements]
            if any(not math.isfinite(v) or not 0 <= v <= 1 for v in rates):
                raise ValueError
            add('lone_byte_share', sum(int(r['tokens'])*v for r,v in zip(measurements,rates))/sum(int(r['tokens']) for r in measurements), 'ratio', 'Sum(tokens × measured fragment rate) / tokens across unique native text items; includes partial-character tokens')
        except (KeyError, TypeError, ValueError):
            row['lone_byte_reason'] = 'No valid fragment-rate measurement for every source item.'
        if price:
            cost, english_cost = _usd(n, price), _usd(e, price)
            # Reconcile against the original checker independently of this projection.
            expected = baseline[prefix+'monthly_inr']/float(fx['inr_per_usd'])
            if not math.isclose(cost*volume/n['chat_count'], expected, rel_tol=1e-9, abs_tol=1e-9):
                raise BillingUnavailable('USD cost differs from the existing baseline checker')
            add('monthly_usd', cost*volume/n['chat_count'], 'USD', 'USD content cost of source requests × monthly conversations / source conversations')
            add('per_conversation_usd', cost/n['chat_count'], 'USD', 'Source billed USD content cost / source conversations')
            add('per_1000_conversations_usd', cost/n['chat_count']*1000, 'USD', 'Cost per conversation × 1000')
            add('per_reply_usd', cost/n['requests'], 'USD', 'Source billed USD content cost / completed replies')
            add('english_monthly_usd', english_cost*volume/n['chat_count'], 'USD', 'Same content in measured English tokens, at the identical provider input/output prices and volume')
            add('language_tax_usd', (cost-english_cost)*volume/n['chat_count'], 'USD', '(Native content USD cost − English content USD cost) × monthly conversations / source conversations')
            if english_cost:
                add('language_tax_percent', (cost/english_cost-1)*100, 'percent', '(Native USD cost / English USD cost − 1) × 100')
                add('cost_multiplier', cost/english_cost, 'ratio', 'Native billed USD cost / English billed USD cost')
            add('input_price_usd', float(price['input_per_mtok_usd']), 'USD', 'Verified quoted USD input price per million tokens')
            add('output_price_usd', float(price['output_per_mtok_usd']), 'USD', 'Verified quoted USD output price per million tokens')
            add('input_per_conversation', n['billed_input']/n['chat_count'], 'tokens', 'Billed source input / conversations')
            add('output_per_conversation', n['billed_output']/n['chat_count'], 'tokens', 'Billed source output / conversations')
            add('system_cost_share', baseline[prefix+'system_prompt_cost_share'], 'ratio', 'Quoted system-input cost / quoted total input and output cost')
        else:
            row['price_reason'] = 'No verified input and output price for this tokenizer.'
        models.append(row)
    own = config['model_in_use']
    if own not in native:
        raise BillingUnavailable('Company tokenizer has no paired measurements')
    values = {(r['chat_id'],int(r['turn']),r['part']):int(r['tokens']) for r in counts if r['tokenizer_spec']==own and r['lang_variant']==language}
    chats = defaultdict(list)
    for item in items:
        if item['part']!='system_prompt': chats[item['chat_id']].append(item)
    ordered = sorted(chats, key=lambda k:(sum(i['part']=='assistant' for i in chats[k]),k))
    chat_id = ordered[(len(ordered)-1)//2]
    system = values[('__system__',0,'system_prompt')]
    history, last_user, cumulative = system, 0, 0
    for item in sorted(chats[chat_id],key=lambda i:int(i['turn'])):
        value = values[(chat_id,int(item['turn']),item['part'])]
        if item['part']=='assistant':
            cumulative += history
            fields = {}
            for name, amount in dict(input=history,system=system,new_user=last_user,replayed_history=history-system-last_user,output=value,cumulative_input=cumulative,transcript_so_far=history+value).items():
                fields[name]=put(own,f'staircase/{chat_id}/{item["turn"]}/{name}',amount,'tokens','Exact content-token reconstruction at this completed reply from source turn rows')
            staircase.append(dict(turn=item['turn'], fields=fields))
        else:
            last_user=value
        history += value
    first = next(i for i in chats[chat_id] if i['part']=='user')
    return metrics, models, dict(chat_id=chat_id,selection='Lower median by completed reply count; ties ordered by chat ID',steps=staircase), dict(native=first['native'],english=first['en'],chat_id=chat_id,turn=first['turn'])


def build_billing(report, events, *, logger=None):
    logger = logger or JsonlLogger(run_id=report.get('id'))
    world = EventWorld(events)
    inputs = _source_ids(report)
    snapshot, prices, fx = (world.verify(inputs[k]) for k in ('snapshot','prices','fx'))
    # Generate source metrics, then run the unmodified server Checker over them.
    original = baseline_metrics(snapshot, prices['rows'], fx)
    checker = Checker(SimpleNamespace(world=world), logger=logger)
    verified, rejected = checker.check(make_claims(original,'baseline',inputs))
    if rejected or len(verified)!=len(original):
        raise BillingUnavailable('The baseline checker could not authenticate the source measurements')
    baseline = {c['id']:c['value'] for c in verified}
    # Explicit English selector is a sourced derivation, not a new measurement.
    english_snapshot=copy.deepcopy(snapshot)
    english_snapshot['config']['language']='en'
    english_snapshot['supports']=[inputs['snapshot']]
    source=dict(snapshot_source=inputs['snapshot'],kind='Deterministic billing transformation',source='World Model bilingual SQL snapshot',
                at=fx.get('fetched_at',snapshot['config'].get('fetched_at','')),fetched_at=world.records[inputs['snapshot']]['provenance']['fetched_at'],
                query='Select the already measured English variant for identical whole-chat billing',time_window=world.records[inputs['snapshot']]['provenance']['time_window'],run_id=report['id'])
    source['at']=source['fetched_at']
    english_id=world.derive(english_snapshot,source,'billing-english-'+report['id'])
    english_inputs={**inputs,'snapshot':english_id}
    english_metrics=baseline_metrics(english_snapshot,prices['rows'],fx)
    _, english_dropped=checker.check(make_claims(english_metrics,'baseline',english_inputs))
    if english_dropped:
        raise BillingUnavailable('English-content baseline failed deterministic checking')
    rows=billed_tokens(snapshot['items'],snapshot['counts'])
    native={r['tokenizer_spec']:r for r in rows if r['lang_variant']==snapshot['config']['language']}
    english={r['tokenizer_spec']:r for r in rows if r['lang_variant']=='en'}
    metrics,models,staircase,default_text=_calculate(snapshot,prices['rows'],native,english,baseline,fx)
    again,_,_,_=_calculate(copy.deepcopy(snapshot),copy.deepcopy(prices['rows']),native,english,baseline,fx)
    if _canonical(metrics)!=_canonical(again):
        raise BillingUnavailable('Billing recomputation differs')
    for model in models:
        if model['price']:
            spec=model['tokenizer']
            en_usd=english_metrics[f'baseline/{spec}/monthly_inr']/float(fx['inr_per_usd'])
            if not math.isclose(metrics[model['fields']['english_monthly_usd']]['value'],en_usd,rel_tol=1e-9,abs_tol=1e-9):
                raise BillingUnavailable('English USD cost differs from the existing checker')
    source_ids=list(inputs.values())+[english_id]
    claims=[dict(id=k,text=k,value=v['value'],unit=v['unit'],verified=True,evidence_ids=source_ids,
                 recompute=dict(operation='billing_view',metric=k,formula=v['formula'],inputs={**inputs,'english_snapshot':english_id},
                                checker='Existing Checker baseline and English selector + billed_tokens/cost_usd reconciliation + deterministic projection recomputation')) for k,v in metrics.items()]
    # Recheck financial claims from the report before canonicalising its legacy INR.
    money_claims=[c for c in report.get('claims',[]) if c.get('verified') is True and c.get('unit')=='INR']
    checked_money,dropped_money=checker.check(money_claims)
    checked_money_by_id={c['id']:c for c in checked_money}
    canonical_money={}
    for c in checked_money:
        fx_id=c['recompute']['inputs'].get('fx')
        rate=world.verify(fx_id).get('inr_per_usd') if fx_id else None
        if rate and math.isfinite(float(rate)) and float(rate)>0:
            canonical_money[c['id']]=dict(value=float(Decimal(str(c['value']))/Decimal(str(rate))),unit='USD',verified=True,
                                          evidence_ids=c['evidence_ids'],legacy_fx=fx_id,formula='Original checked INR amount / its original recorded INR per USD rate')
    own=next(m for m in models if m['tokenizer']==snapshot['config']['model_in_use'])
    own_month=metrics.get(own['fields'].get('monthly_usd'),{}).get('value')
    fixes=[]
    for i,fix in enumerate(report.get('fixes',[])):
        c=canonical_money.get(fix.get('claim_id'))
        entry={**fix,'fields':{},'tested':bool(fix.get('experiment_evidence_ids'))}
        if c is not None and own_month is not None:
            saving=c['value'];prefix=f'billing/fix/{i}/'
            comparable=not (fix.get('claim_id','').startswith('experiment/') and (report.get('experiment') or {}).get('accounting_version')!=2)
            entry['group']='would_cost_more' if saving<0 else 'saving'
            for field,value,unit,formula in [('saving_usd',saving,'USD','Original checked saving converted using its recorded FX'),('saving_percent',saving/own_month*100,'percent','Saving / today monthly cost × 100')]:
                key=prefix+field;entry['fields'][field]=key
                claims.append(dict(id=key,text=field,value=value,unit=unit,verified=True,evidence_ids=c['evidence_ids'],recompute=dict(operation='billing_fix',formula=formula,inputs=inputs,source_claim=fix['claim_id'])))
            if comparable:
                key=prefix+'after_monthly_usd';entry['fields']['after_monthly_usd']=key
                claims.append(dict(id=key,text='After-fix monthly cost',value=own_month-saving,unit='USD',verified=True,evidence_ids=c['evidence_ids'],recompute=dict(operation='billing_fix',formula='Today monthly cost − this individual fix saving; fixes are independent alternatives',inputs=inputs,source_claim=fix['claim_id'])))
                # Expose the checked split for separately repricing input/output in what-if.
                spec=snapshot['config']['model_in_use'];n=native[spec];price=select_price(prices['rows'],spec)
                after_input,after_output=n['billed_input'],n['billed_output']
                target=fix.get('tokenizer') if fix.get('lever')=='model_switch' else None
                if target and target in native:
                    n=native[target];after_input,after_output=n['billed_input'],n['billed_output'];price=select_price(prices['rows'],target)
                elif fix['claim_id'].startswith('experiment/'):
                    experiment_id=checked_money_by_id[fix['claim_id']]['recompute']['inputs'].get('experiment')
                    experiment=world.verify(experiment_id) if experiment_id else {}
                    original_system=next(int(r['tokens']) for r in snapshot['counts'] if r['tokenizer_spec']==spec and r['lang_variant']==snapshot['config']['language'] and r['part']=='system_prompt')
                    if 'changed_system_tokens' in experiment:
                        after_input-=(original_system-int(experiment['changed_system_tokens']))*n['requests']
                    else:
                        after_input=None
                elif fix['claim_id'].endswith('/english_system_monthly_saving_inr'):
                    after_input-=baseline[f'baseline/{spec}/english_system_input_saved']
                elif fix['claim_id'].endswith('/half_answers_monthly_saving_inr'):
                    after_input-=baseline[f'baseline/{spec}/assistant_tokens']/2
                    after_output/=2
                else:
                    after_input=None
                if after_input is not None and price:
                    split=dict(after_input_per_conversation=after_input/n['chat_count'],after_output_per_conversation=after_output/n['chat_count'],
                               after_input_price_usd=float(price['input_per_mtok_usd']),after_output_price_usd=float(price['output_per_mtok_usd']))
                    reconstructed=snapshot['config']['monthly_chats']*(split['after_input_per_conversation']*split['after_input_price_usd']+split['after_output_per_conversation']*split['after_output_price_usd'])/1_000_000
                    if math.isclose(reconstructed,own_month-saving,rel_tol=1e-9,abs_tol=1e-9):
                        for field,value in split.items():
                            key=prefix+field;entry['fields'][field]=key
                            claims.append(dict(id=key,text=field,value=value,unit='USD' if 'price_usd' in field else 'tokens',verified=True,evidence_ids=c['evidence_ids'],recompute=dict(operation='billing_fix',formula='After-fix content split reconciled to the existing checked after-cost; hypothetical where the fix is untested',inputs=inputs,source_claim=fix['claim_id'])))
            else:
                entry['comparison_reason']='Archived experiment used sampled-last-turn accounting; it cannot form a whole-chat after-cost.'
        else:
            entry['group']='not_measured';entry['comparison_reason']='No checked comparable money claim.'
        fixes.append(entry)
    values={c['id']:c['value'] for c in claims}
    fixes.sort(key=lambda f: (f.get('group')=='not_measured', -values.get(f.get('fields',{}).get('saving_usd'), 0)))
    quality={}
    report_claims={c['id']:c for c in report.get('claims',[]) if c.get('verified') is True}
    for variant,prefix in [('ab','quality/'),('aa','quality/aa/')]:
        counts=[report_claims.get(prefix+k) for k in ('passed','judged')]
        if not all(counts): continue
        try:
            ids=counts[0]['evidence_ids']
            verdict=next(world.verify(eid) for eid in ids if world.records[eid]['kind']=='quality_verdict')
            pairs=verdict['pairs']
            if len({p['chat_id'] for p in pairs})!=len(pairs) or len(pairs)>20:
                raise ValueError('Invalid quality sample')
            if sum(p.get('same_facts') is True for p in pairs)!=counts[0]['value'] or sum(type(p.get('same_facts')) is bool for p in pairs)!=counts[1]['value']:
                raise ValueError('Quality dots differ from checked counts')
            quality[variant]=dict(pairs=[{k:p.get(k) for k in ('chat_id','same_facts','reason')} for p in pairs],evidence_ids=ids)
        except (BillingUnavailable,KeyError,StopIteration,ValueError):
            quality[variant]=dict(reason='Quality pair records are missing or differ from the checked report.')
    used=set(source_ids)
    for c in checked_money:
        used.update(c['evidence_ids'])
    # Only named receipt support is exposed; unrelated investigations stay out of the response.
    for field,value in [('reported_checked',sum(c.get('verified') is True for c in report.get('claims',[]))),('reported_dropped',len(report.get('dropped_claims',[])))]:
        claims.append(dict(id='billing/trust/'+field,text=field,value=value,unit='integer',verified=True,evidence_ids=source_ids,recompute=dict(operation='report_counts',formula='Count of recorded checker entries in this report; original verdicts are retained',inputs=inputs)))
    result=dict(schema_version='billing-1',id=report['id'],company=report.get('company'),language=snapshot['config']['language'],tokenizer=snapshot['config']['model_in_use'],
                status='checked',base='USD',claims=claims,models=models,headline=own['fields'],composition=own['composition'],staircase=staircase,
                fixes=fixes,quality=quality,report_money=canonical_money,default_text=default_text,
                records=[world.records[eid] for eid in sorted(used)],dropped_claims=dropped_money,
                limitations=['Quoted provider scenario, not an invoice. Content tokens only; excludes templates, retries and cache discounts.',
                             'English comparison uses paired measured translations; native review is pending.',
                             'Cacheable share means identical system-prefix input, not a verified provider cache discount.',
                             'Every fix is an independent alternative to today; savings are never added together.'])
    logger.write('billing','recomputed',ok=True,investigation_id=report['id'],claims=claims,inputs=inputs,english_snapshot=english_id,
                 checker_rejected=dropped_money,source='World Model recorded Zetaris SQL',query='billing_view over authenticated baseline, prices and paired English counts',
                 fetched_at=datetime.now(timezone.utc).isoformat(),time_window=source['time_window'])
    for event in world.derived:
        logger.write('billing_world_events','derived_evidence',world_event=event)
    return result
