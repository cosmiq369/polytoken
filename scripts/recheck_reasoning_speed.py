#!/usr/bin/env python3
"""Reverify a completed pre-correction report from existing evidence, without calls."""
import argparse
import copy
import json
from pathlib import Path

from polytoken.checker import Checker
from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.world_model import WorldModel
from polytoken.tools import now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report')
    args = parser.parse_args()
    path = Path(args.report)
    original = json.loads(path.read_text())
    if original['status'] == 'running':
        raise ValueError('Wait for the job to finish')
    logger = JsonlLogger(run_id=original['id'])
    report = copy.deepcopy(original)
    with WorldModel(logger=logger) as world:
        events = {e['event_id']: e for e in world.events()}
        catalogues = [events[eid] for eid in report['evidence_ids'] if 'serving_verification' in events[eid]['payload']]
        catalogue = catalogues[-1]
        reasoning = {model for model, record in catalogue['payload']['serving_verification'].items()
                     if record.get('generation_options', {}).get('reasoning_effort')}
        old_ids = {c['recompute']['inputs']['speed'] for c in report['claims'] if c['recompute']['operation'] == 'speed'}
        store = EvidenceStore(world)
        replacements = {}
        for old in old_ids:
            payload = copy.deepcopy(events[old]['payload'])
            changed = False
            for row in payload['runs']:
                if row['model'] in reasoning and row.get('throughput_supported') is not False:
                    row['throughput_supported'] = False
                    row.pop('output_tokens_per_s', None)
                    row['throughput_note'] = 'Unavailable: provider usage does not separate reasoning from visible tokens.'
                    changed = True
            if not changed:
                continue
            payload['supports'] = [old, catalogue['event_id']]
            source = dict(kind='Offline throughput accounting correction', at=now(), fetched_at=now(),
                          query={'operation': 'exclude inseparable reasoning throughput', 'original_speed': old},
                          time_window=events[old]['provenance']['time_window'])
            eid = store.add('timed_call', payload, source=source, supports=payload['supports'])
            replacements[old] = eid
            report['evidence_ids'].append(eid)
        for claim in report['claims']:
            if claim['recompute']['operation'] == 'speed':
                old = claim['recompute']['inputs']['speed']
                claim['recompute']['inputs']['speed'] = replacements.get(old, old)
                claim['evidence_ids'] = [replacements.get(eid, eid) for eid in claim['evidence_ids']]
        report['claims'], dropped = Checker(store, logger).check(report['claims'])
        assert all(r['id'].startswith('speed/output_tokens_per_s/') for r in dropped), dropped
        report['dropped_claims'].extend(dropped)
        report['throughput_status'] = 'unavailable; inseparable reasoning usage'
        report['limitations'].append('Throughput was rechecked offline against the recorded reasoning settings; unsupported throughput claims were dropped. Original timing observations are unchanged.')
        if replacements:
            archive = path.with_name(path.stem + '_before_throughput_correction.json')
            if not archive.exists():
                archive.write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n')
            text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
            path.write_text(text)
            (Path('logs/investigations') / (report['id'] + '.json')).write_text(text)
            logger.write('agent', 'report_reverified', report=report)
            JsonlLogger('logs/sample', run_id=report['id']).write('agent_v2_validation', 'throughput_recheck',
                report=str(path), prior_report=str(archive), dropped=dropped, evidence_ids=list(replacements.values()), ok=True,
                source='Existing World Model evidence', query='exclude inseparable reasoning throughput', fetched_at=now())
        print(f"Reverified {len(report['claims'])} claims; dropped {len(dropped)} unsupported throughput claims; no network calls.")


if __name__ == '__main__':
    main()
