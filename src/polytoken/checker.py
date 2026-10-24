"""Fail-closed numeric claims, recomputed exclusively from World Model events."""
import hashlib
import json
import math

from .agent.calculations import baseline_metrics, experiment_metrics, quality_metrics, speed_metrics
from .meterless.markovian import run_efficiency


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def unit_for(key, value):
    if 'inr' in key:
        return 'INR' if 'per_rupee' not in key else 'INR per INR input price per million tokens'
    if 'percent' in key:
        return 'percent'
    if any(x in key for x in ('_share', 'ratio', 'ci_low', 'ci_high')):
        return 'ratio'
    if 'tokens_per_s' in key:
        return 'tokens/s'
    if any(x in key for x in ('ttft_s', 'latency_s', 'duration_s', 'remaining_s')):
        return 'seconds'
    return 'integer' if type(value) is int else 'number'


class Checker:
    def __init__(self, store, logger=None):
        self.store, self.logger = store, logger

    def check(self, claims):
        events = {e['event_id']: e for e in self.store.world.events()}
        checked, dropped, cache = [], [], {}
        verified_events = {}

        def verify(eid, visiting=None):
            if eid in verified_events:
                return verified_events[eid]
            visiting = set() if visiting is None else visiting
            if eid in visiting:
                raise ValueError('Cyclic evidence support')
            event = events[eid]
            digest = hashlib.sha256(f"{event['kind']}|{event['item_key']}|{_canonical(event['payload'])}|{_canonical(event['provenance'])}".encode()).hexdigest()[:24]
            if event['event_id'] != 'evt_' + digest:
                raise ValueError('Stored evidence was tampered with')
            self.store.world._provenance(event['provenance'], strict=True)
            # Failed observations are valid evidence of missing/completed counts;
            # calculators explicitly exclude them from measurements and money.
            for parent in event['payload'].get('supports', []):
                verify(parent, visiting | {eid})
            verified_events[eid] = event['payload']
            return event['payload']

        for claim in claims:
            try:
                ids = claim['evidence_ids']
                if not ids:
                    raise ValueError('No evidence')
                evidence = {eid: verify(eid) for eid in ids}
                recipe = claim['recompute']
                if set(recipe['inputs'].values()) != set(ids):
                    raise ValueError('Recipe inputs do not match evidence')
                key = _canonical(recipe)
                if key not in cache:
                    args = {name: evidence[eid] for name, eid in recipe['inputs'].items()}
                    op = recipe['operation']
                    if op in ('baseline', 'hypotheses'):
                        result = baseline_metrics(args['snapshot'], args['prices']['rows'], args['fx'])
                        if op == 'hypotheses':
                            spec = args['snapshot']['config']['model_in_use']
                            own = result.get('baseline/' + spec + '/monthly_inr')
                            result = {'hypotheses/' + s + '/switch_monthly_saving_inr': own - value
                                      for k, value in result.items() if k.startswith('baseline/') and k.endswith('/monthly_inr')
                                      for s in [k[len('baseline/'):-len('/monthly_inr')]] if own is not None and s != spec}
                    elif op == 'experiment':
                        result = experiment_metrics(args['experiment'], args['snapshot'], args['prices']['rows'], args['fx'])
                    elif op == 'quality':
                        result = quality_metrics(args['quality'])
                    elif op == 'speed':
                        result = speed_metrics(args['speed'])
                    elif op == 'markovian':
                        result = {}
                        for index, run in enumerate(args['runs']['runs']):
                            actual = run_efficiency(run['chunks'], run['chunkConfig']) if 'chunks' in run else run['actual']
                            net = actual['standardCost'] - actual['markovianCost']
                            result[f'markovian/{index}/net_tokens'] = net
                            result[f'markovian/{index}/net_percent'] = net / actual['standardCost'] * 100 if actual['standardCost'] else 0.
                    elif op == 'budget':
                        result = {f'budget/{k}': v for k, v in args['budget'].items() if type(v) in (int, float)}
                    else:
                        raise ValueError('Unsupported recomputation')
                    cache[key] = result
                recomputed = cache[key][claim['id']]
                value = claim['value']
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('Non-finite or nonnumeric claim')
                if type(recomputed) is int:
                    valid = type(value) is int and value == recomputed
                elif claim['unit'] == 'INR':
                    valid = abs(value - recomputed) <= .01
                else:
                    valid = math.isclose(value, recomputed, rel_tol=1e-9, abs_tol=0.)
                if not valid:
                    raise ValueError('Value differs from recomputation')
                checked.append({**claim, 'verified': True})
            except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                dropped.append({'id': claim.get('id'), 'reason': str(exc)})
        if self.logger:
            self.logger.write('checker', 'checked', accepted=len(checked), dropped=dropped)
        return checked, dropped


def make_claims(metrics, operation, inputs):
    return [{'id': key, 'text': key.replace('/', ' '), 'value': value,
             'unit': unit_for(key, value), 'evidence_ids': list(inputs.values()),
             'recompute': {'operation': operation, 'inputs': inputs}}
            for key, value in metrics.items()]
