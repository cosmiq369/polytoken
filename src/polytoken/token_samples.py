"""Paired token receipts; never relabel old encodings as new measurements."""
import json
from types import SimpleNamespace

from .billing_view import EventWorld, archived_events
from .checker import Checker, make_claims
from .paths import ROOT


def pair_metrics(native, english):
    for row in (native, english):
        if row.get('ok') is not True or not row.get('tokenizer_sha256'):
            raise ValueError('No successful encoding receipt')
        pieces=[p for p in row['pieces'] if p['kind']=='token']
        if not pieces or len(pieces)!=row['count'] or ''.join(p['text'] for p in row['pieces'])!=row['text']:
            raise ValueError('Token pieces do not reproduce the stored count and text')
    if native['tokenizer']!=english['tokenizer'] or native['tokenizer_sha256']!=english['tokenizer_sha256']:
        raise ValueError('Paired encodings must use identical tokenizer files')
    return {'token_pair/native_tokens':native['count'],'token_pair/english_tokens':english['count'],
            'token_pair/ratio':native['count']/english['count']}


def samples(log_dir, logger):
    sample=json.loads((ROOT/'data/reference/token_samples.json').read_text())
    world=EventWorld(archived_events(log_dir))
    encodings={(e['payload'].get('text'),e['payload'].get('tokenizer')):e
               for e in world.events() if e['payload'].get('pieces')}
    result=[]
    for variant,label in [('native','Telugu (native script)'),('tenglish','Tenglish (Telugu in English letters + English words)')]:
        models=[]
        for (text,spec),event in encodings.items():
            if text!=sample[variant]:continue
            en=encodings.get((sample['english'],spec))
            if not en:continue
            try:
                metrics=pair_metrics(event['payload'],en['payload'])
                claims,dropped=Checker(SimpleNamespace(world=world),logger).check(make_claims(metrics,'token_pair',{'native':event['event_id'],'english':en['event_id']}))
                if dropped:continue
                models.append({'tokenizer':spec,'record':event['payload'],'english':en['payload'],'claims':claims,
                               'evidence':[event,en]})
            except (ValueError,KeyError,TypeError):continue
        result.append({'variant':variant,'label':label,'text':sample[variant],'english':sample['english'],
                       'review_status':sample['review_status'],'review_note':sample['review_note'],'source':sample['source'],
                       'models':models})
    return result
