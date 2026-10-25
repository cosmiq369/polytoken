"""Separate hosted-job deadline and evidence-backed successful-call cache."""
import hashlib
import json

from .budget import BudgetGuard


class JobBudget(BudgetGuard):
    def __init__(self, reasoning, *, wall_s=1800):
        super().__init__(clock=reasoning.clock, wall_s=wall_s)
        # Share physical reasoning, judge, hosted and SQL attempt counters.
        self.counts = reasoning.counts
        self.lock = reasoning.lock


def cache_key(model, system, chat_id, user, max_tokens, generation_options=None):
    return hashlib.sha256(json.dumps({
        'model': model, 'system_sha256': hashlib.sha256(system.encode()).hexdigest(),
        'chat_id': chat_id, 'user': user, 'max_tokens': max_tokens, 'temperature': 0,
        'generation_options': generation_options or {}, 'version': 1,
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cached_calls(store):
    """Only content-addressed successful raw calls are eligible for reuse."""
    result = {}
    for event in store.world.events():
        payload = event['payload']
        if not payload.get('ok') or not payload.get('cache_key'):
            continue
        canonical = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(f"{event['kind']}|{event['item_key']}|{canonical(payload)}|{canonical(event['provenance'])}".encode()).hexdigest()[:24]
        if event['event_id'] == 'evt_' + digest:
            result[payload['cache_key']] = (payload, event['event_id'])
    return result
