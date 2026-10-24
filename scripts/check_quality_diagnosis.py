#!/usr/bin/env python3
"""Verify archived quality diagnosis sources/counts, not semantic annotations.

No services, model calls, contract edits, or report-score updates. Semantic
assessments remain assistant annotations requiring native-speaker review.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def check(root):
    base = root / 'logs/sample'
    events = {}
    for line in (base / 'agent_v2_world_events.jsonl').read_text().splitlines():
        event = json.loads(line)['world_event']
        digest = hashlib.sha256('|'.join((event['kind'], event['item_key'],
                  canonical(event['payload']), canonical(event['provenance']))).encode()).hexdigest()[:24]
        assert event['event_id'] == 'evt_' + digest, 'World Model event hash mismatch'
        assert event['event_id'] not in events, 'Duplicate World Model event'
        events[event['event_id']] = event
    records = [json.loads(line) for line in (base / 'agent_v2_quality_diagnosis.jsonl').read_text().splitlines()]
    rows = [r for r in records if r['type'] == 'pair_review']
    summaries = [r for r in records if r['type'] == 'summary']
    assert len(summaries) == 1 and len(records) == len(rows) + 1
    assert len({r['chat_id'] for r in rows}) == len(rows) == 40
    metrics = {}
    for company, cap in [('samudra', 200), ('swara', 600)]:
        report = json.loads((base / f'agent_{company}_v2_report.json').read_text())
        claims = {c['id']: c for c in report['claims']}
        eid, = report['experiment']['evidence_ids']
        qid = claims['quality/passed']['recompute']['inputs']['quality']
        exp = events[eid]['payload']
        verdict = events[qid]['payload']
        assert verdict['sample_status'] == 'complete' and eid in verdict['supports']
        pairs = {p['chat_id']: p for p in exp['pairs']}
        judged = {p['chat_id']: p for p in verdict['pairs']}
        selected = [r for r in rows if r['company'] == company]
        assert len(selected) == len(pairs) == len(judged) == 20
        assert {r['chat_id'] for r in selected} == set(pairs) == set(judged)
        for row in selected:
            chat = row['chat_id']
            assert row['pair'] == pairs[chat] and row['judge'] == judged[chat], f'Altered source: {chat}'
            assert row['experiment_event_id'] == eid and row['quality_event_id'] == qid
            assert row['snapshot_event_id'] == exp['supports'][0]
            assert row['max_tokens'] == cap and row['score_override'] is None
            assert row['official_review_status'] == row['judge']['review_status'] == 'pending'
            assert row['finish_reason_available'] is False
            for variant in ('original', 'changed'):
                reply = pairs[chat][variant]
                assert reply['ok'] and reply['text'].strip() and 'finish_reason' not in reply
                assert row['cap_hit'][variant] == (reply['usage']['completion_tokens'] == cap)
            assert row['provenance']['query'] == {'experiment': eid, 'quality': qid, 'chat_id': chat}
            assert all(row['provenance'][k] for k in ('source', 'query', 'time_window', 'fetched_at'))
        metrics[company] = {
            'pairs': len(selected),
            'judged': sum(type(r['judge']['same_facts']) is bool for r in selected),
            'passed': sum(r['judge']['same_facts'] is True for r in selected),
            'assessments': dict(Counter(r['assessment'] for r in selected)),
            'variants': {variant: {
                'cap_hit': sum(r['cap_hit'][variant] for r in selected),
                # Recount subjective ending labels; do not pretend to prove truncation.
                'visible_incomplete_ending': sum(r['visible_incomplete_ending'][variant] for r in selected),
                'provider_completion_min': min(r['pair'][variant]['usage']['completion_tokens'] for r in selected),
                'provider_completion_max': max(r['pair'][variant]['usage']['completion_tokens'] for r in selected),
            } for variant in ('original', 'changed')},
        }
        for key in ('passed', 'judged'):
            assert metrics[company][key] == claims['quality/' + key]['value']
    assert metrics == summaries[0]['metrics'], 'Diagnosis aggregate mismatch'
    return {'source_events_authenticated': len(events), 'pairs_verified': len(rows),
            'metrics': metrics, 'semantic_annotations_verified': False}


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[1]), indent=2))
