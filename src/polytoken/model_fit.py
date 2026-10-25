"""Deterministic workload profiles and model/provider scenarios, never model prose.

All inputs are authenticated World Model payloads populated from Zetaris SQL.
The classifier is deliberately a disclosed lexical heuristic, not a language model.
"""
from collections import Counter
from decimal import Decimal
import hashlib
import math
import re

from .measurement_report import billed_tokens
from .prices import cost_usd, validate_price

SCRIPT_BUCKETS = ('native_script', 'romanized', 'code_mixed', 'unknown')
INDIC_LATIN = set('na naa nenu naaku ninna ee undi unda undaa unte unna cheyyali cheyyaali cheyyala cheyyandi chudandi chudaali cheppandi chestunna chesanu chesara chesaaraa ayyindi ravatledu avutunda avutunnayi saripovatledu matram maatram lo ki ga kuda ela ekkada eppudu emi em ikkada malli mee meeru mari ippudu taruvaata kaavaali ledu lekunda vaadutunnaanu prastuta pathakam ant arjaalam antarjaalam samasya nirdhaarinchandi sahaaya adhikaarika chellimpu vivaraalu punaruddharana kaaledu inkaa nemmadigaa maatlaadatam baagundi udayam saayantram use next steps vachaka chesukondi alage naaku hai hain mera meri mere mujhe mein ka ki ke ko se nahi kya kaise karna kar kijiye chahiye ho hoon raha rahi aaya karta dikh din dobara mat batayiye yahan kabhi chesaaraa telusukovaali andubaatu velle pradesam chusi daanini aapadaaniki maatram'.split())
# Domain English words recognized for a conservative lexical share. Unknown Latin
# words are not silently called English; numbers are excluded from this denominator.
ENGLISH_TERMS = set('app android ios mobile data calls work payment pending history status check support ticket update issue network phone restart bill extra charge details plan current change available plans compare price validity confirm select sim miss block request official process otp share travel roaming coverage destination charges screen new settings personal error text open save already tried steps next step help upi refund sip auto debit notification savings account statement download kyc card limit neft transfer receipt login transaction mandate date investment recommendation menu range number sms link options approval guarantee pin password screenshot report'.split())
# English tokens that occur naturally in romanized templates should mark code mix,
# but not generic transliteration fragments that are also English homographs.
INDIC_LATIN -= ENGLISH_TERMS
INDIC_LATIN.discard('use')


def script_mix(text, language):
    words = [w for w in re.findall(r'[a-z]+|[\u0900-\u097f\u0c00-\u0c7f]+', text.casefold()) if any(c.isalpha() for c in w)]
    latin = [w for w in words if w.isascii() and w.isalpha()]
    native = sum(1 for ch in text if ('\u0c00' <= ch <= '\u0c7f' if language == 'te' else '\u0900' <= ch <= '\u097f') and ch.isalpha())
    indic = sum(w in INDIC_LATIN for w in latin)
    english = sum(w in ENGLISH_TERMS for w in latin)
    if native:
        bucket = 'code_mixed' if english else 'native_script'
    elif indic:
        bucket = 'code_mixed' if english else 'romanized'
    else:
        bucket = 'unknown'
    return dict(bucket=bucket, english_terms=english, words=len(words), indic_latin_words=indic)


def quote_key(price):
    return hashlib.sha256((price['model']+'|'+price['provider']).encode()).hexdigest()[:16]


def _latency(snapshot, price, timings):
    """No cross-model, provider, workload, or cached timing substitution."""
    config=snapshot['config']
    if config.get('channel') != 'voice':
        return 'not required', None
    rows=[r for r in timings.get('runs', []) if r.get('ok') is True
          and not r.get('cache_hit') and r.get('finish_reason') == 'stop'
          and r.get('model') == price['model'] and r.get('provider') == price['provider']
          and r.get('company') == config['company'] and r.get('dataset_version') == config.get('dataset_version')
          and r.get('measurement_run_ids') == sorted({x['run_id'] for x in snapshot['counts']})
          and type(r.get('latency_s')) in (int,float) and math.isfinite(r['latency_s']) and r['latency_s'] > 0
          and r.get('source') and r.get('query') and r.get('fetched_at') and r.get('time_window')]
    if len({r.get('request_id') for r in rows if r.get('request_id')}) < 4:
        return 'unverified', None
    maximum=max(r['latency_s'] for r in rows)
    return ('within target' if maximum <= float(config['latency_target_s']) else 'exceeds target'), maximum


def calculate_fit(snapshot, prices, timings=None):
    timings=timings or {}
    config=snapshot['config']; language=config['language']
    rows=billed_tokens(snapshot['items'],snapshot['counts'])
    actual={r['tokenizer_spec']:r for r in rows if r['lang_variant']==language}
    english={r['tokenizer_spec']:r for r in rows if r['lang_variant']=='en'}
    users=[i for i in snapshot['items'] if i['part']=='user']
    turns=[i for i in snapshot['items'] if i['part']!='system_prompt']
    if not users or not actual: raise ValueError('No workload evidence')
    detected=[script_mix(i['native'],language) for i in users]
    counts=Counter(d['bucket'] for d in detected)
    chats={i['chat_id'] for i in turns}
    own=actual[config['model_in_use']]
    all_detected=[script_mix(i['native'],language) for i in turns]
    denominator=sum(d['words'] for d in all_detected)
    metrics={f'profile/{bucket}_share': counts[bucket]/len(users) for bucket in SCRIPT_BUCKETS}
    metrics.update({'profile/conversations':len(chats),'profile/user_turns':len(users),
        'profile/turns_per_conversation':len(turns)/len(chats),
        'profile/replies_per_conversation':own['requests']/len(chats),
        'profile/answer_billed_share':own['billed_output']/(own['billed_input']+own['billed_output']),
        'profile/english_terms_share':sum(d['english_terms'] for d in all_detected)/denominator if denominator else 0.,
        'profile/monthly_conversations':int(config['monthly_chats']),
        'profile/latency_target_s':float(config['latency_target_s'])})
    ranked=[]
    for p in prices:
        validate_price(p)
        spec=p['tokenizer_spec']
        if p['verified'] is not True or p['input_per_mtok_usd'] is None or p['output_per_mtok_usd'] is None or spec not in actual: continue
        n,e=actual[spec],english[spec]
        key=quote_key(p);prefix='fit/'+key+'/'
        usd=cost_usd(p,n['billed_input'],n['billed_output'])*Decimal(1000)/n['chat_count']
        total=n['billed_input']+n['billed_output']; en_total=e['billed_input']+e['billed_output']
        metrics[prefix+'usd_per_1000']=float(usd)
        metrics[prefix+'token_ratio']=total/en_total
        metrics[prefix+'billed_input']=n['billed_input']
        metrics[prefix+'billed_output']=n['billed_output']
        status,latency=_latency(snapshot,p,timings)
        if latency is not None: metrics[prefix+'latency_s_max']=latency
        ranked.append(dict(key=key,model=p['model'],provider=p['provider'],tokenizer=spec,
            source_url=p['source_url'],fetched_at=p['fetched_at'],cost_claim=prefix+'usd_per_1000',
            ratio_claim=prefix+'token_ratio',latency=status,
            latency_claim=prefix+'latency_s_max' if latency is not None else None,
            quality='verify on your sample'))
    ranked.sort(key=lambda r:(metrics[r['cost_claim']],r['model'],r['provider']))
    # The main ranking contains every distinct model at its cheapest measured
    # quote. Preserve all provider alternatives for receipts and audit.
    models=[];seen=set()
    for r in ranked:
        if r['model'] not in seen:
            models.append(r);seen.add(r['model'])
    eligible=[r for r in ranked if r['latency'] in ('within target','not required')]
    primary=eligible[0] if eligible else None
    candidate=models[0] if models else None
    runner=next((r for r in (eligible if primary else models) if r['model'] != (primary or candidate)['model']),None) if candidate else None
    # Compare a fixed equal input/output token basket, independent of workload.
    # "Cheap" is the lower half of distinct models by that quoted unit price.
    quotes={quote_key(p):p for p in prices}
    unit_order=sorted(models,key=lambda r:(Decimal(str(quotes[r['key']]['input_per_mtok_usd']))+
        Decimal(str(quotes[r['key']]['output_per_mtok_usd'])),r['model'],r['provider']))
    cheap=unit_order[:max(1,(len(unit_order)+1)//2)]
    cheapest=unit_order[0] if unit_order else None
    avoid=max((r for r in cheap if r['model']!=candidate['model'] and
        metrics[r['ratio_claim']]>1 and metrics[r['cost_claim']]>metrics[candidate['cost_claim']]),
        key=lambda r:(metrics[r['ratio_claim']],-unit_order.index(r)),default=None) if candidate else None
    for row in ranked:
        row['monthly_usd']=metrics[row['cost_claim']]*metrics['profile/monthly_conversations']/1000
        row['cost_multiple']=metrics[row['cost_claim']]/metrics[candidate['cost_claim']] if candidate and metrics[candidate['cost_claim']]>0 else None
        row['monthly_claim_ids']=[row['cost_claim'],'profile/monthly_conversations']
        row['multiple_claim_ids']=[row['cost_claim'],candidate['cost_claim']] if candidate else []
    unpriced=sorted(set(actual)-{p['tokenizer'] for p in ranked})
    # unpriced rows must still receive checked ratios; missing prices never become zero dollars.
    for spec in unpriced:
        metrics['fit-only/'+spec+'/token_ratio']=(actual[spec]['billed_input']+actual[spec]['billed_output'])/(english[spec]['billed_input']+english[spec]['billed_output'])
    dominant=max(SCRIPT_BUCKETS,key=lambda k:counts[k])
    reason_ids=[f'profile/{dominant}_share','profile/turns_per_conversation','profile/answer_billed_share','profile/english_terms_share']
    def decision(row, role):
        if row is None:return None
        return dict(**row,reason=(f"Workload: {dominant.replace('_', ' ')} user turns; compare the checked conversation shape, answer share and per-model token ratio. " + ('Highest tokens / English among the lower half of models by equal input/output unit price, above the best content cost; tokenizer penalty drives this avoid choice. This is not a quality rejection.' if role=='avoid' else
            'Lowest quoted price for an equal input/output token basket; workload cost depends on measured token counts.' if role=='unit_price' else
            'Lowest quoted content cost among latency-qualified options.' if role=='recommendation' and config.get('channel')=='voice' else
            'Next lowest quoted cost for a different model; verify quality and any unmeasured latency.' if role=='runner_up' else
            'Lowest quoted content cost on this workload; verify quality before changing models.')),
            reason_claim_ids=[*reason_ids,row['cost_claim'],row['ratio_claim'],*([row['latency_claim']] if row['latency_claim'] else [])])
    view=dict(profile=dict(company=config['company'],display_name=config.get('display_name', config['company']),language=language,role=config.get('role',''),channel=config.get('channel','chat'),
        current_model=config.get('current_model',config['model_in_use']),dominant_script=dominant,
        classifier='Unicode native blocks + versioned Indic Latin and English domain lexicons; unknown retained. User-turn shares; English term share over all conversation words, excluding numbers.',
        answer_share_basis='New output tokens / total billed content tokens on the current tokenizer; replayed answers remain input.',
        review_status='pending'),models=models,provider_quotes=ranked,lowest_unit_price=decision(cheapest,'unit_price'),
        cheap_rule='Lower half of distinct models ranked by the price of an equal input/output token basket; ties by model/provider.',
        tokenizer_fit_only=[dict(tokenizer=s,ratio_claim='fit-only/'+s+'/token_ratio',status='tokenizer fit only') for s in unpriced],
        recommendation=decision(primary,'recommendation'),cost_candidate=decision(candidate,'candidate'),runner_up=decision(runner,'runner_up'),avoid=decision(avoid,'avoid'),
        status='Conditional on quality verification' if primary else 'No model has verified latency for this voice workload' if candidate else 'No verified price available',
        serving_note='Only GPT-OSS passed the recorded serving probe. Stand-in results do not establish quality or latency for another model/provider.',
        limitations=[('Uploaded paired text; translations and native review pending.' if config['company'].startswith('upload_') else 'Fictional paired text; translations and native review pending.'),
            'Content-token estimate with completed history replay; excludes model chat templates, retries, taxes and unpublished caching prices.',
            'Model/provider quotes retain their fetched-at date; no invoice or accuracy guarantee.',
            'Observed timing ranges are sample checks, not latency SLAs.'])
    return metrics,view


def checked_fit(snapshot, prices, timings, verified, inputs):
    """Rebuild all labels and decisions from evidence, and require every number."""
    metrics,view=calculate_fit(snapshot,prices,timings)
    if any(k not in verified or not math.isclose(verified[k],v,rel_tol=1e-9,abs_tol=1e-12) for k,v in metrics.items()):
        return None
    return {**view,'claim_ids':list(metrics),'evidence_ids':list(inputs.values())}


def replay_fit(report, world, logger=None):
    """Never trust a saved recommendation, model label or ranking without sources."""
    from types import SimpleNamespace
    from .checker import Checker
    claims=[c for c in report.get('claims',[]) if c.get('recompute',{}).get('operation')=='model_fit']
    if not claims:return None,[]
    checked,dropped=Checker(SimpleNamespace(world=world),logger).check(claims)
    if dropped or not checked:return None,[]
    inputs=checked[0]['recompute']['inputs']
    if any(c['recompute']['inputs']!=inputs for c in checked):return None,[]
    try:
        snapshot=world.verify(inputs['snapshot'])
        if snapshot['config']['company']!=report['company']:return None,[]
        view=checked_fit(snapshot,world.verify(inputs['prices'])['rows'],world.verify(inputs['timings']),
            {c['id']:c['value'] for c in checked},inputs)
        return view,checked if view else []
    except (KeyError,ValueError,TypeError):
        return None,[]
