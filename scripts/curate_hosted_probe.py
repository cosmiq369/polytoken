#!/usr/bin/env python3
"""Archive every serving observation and raw diagnostic attempt for replay."""
import json
from pathlib import Path
from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.world_model import WorldModel


def main():
    sample = Path('logs/sample')
    rows = [json.loads(line) for line in (sample / 'hosted_probe.jsonl').read_text().splitlines()]
    latest = rows[-1]['run_id']
    run_ids = {r['run_id'] for r in rows} | {'p04b-serving-probe'}
    model_ids = {}
    wanted = set()
    with WorldModel(logger=JsonlLogger()) as world:
        store = EvidenceStore(world)
        for row in rows:
            source = {k: row[k] for k in ('source', 'query', 'time_window', 'fetched_at')}
            source.update(kind='NVIDIA streamed serving probe', at=row['fetched_at'])
            eid = store.add('timed_call', row, source=source)
            wanted.add(eid)
            model_ids.setdefault((row['model'], row['run_id']), []).append(eid)
        events = [e for e in world.events() if e['event_id'] in wanted]
    path = Path('data/reference/nvidia_hosted.json')
    catalogue = json.loads(path.read_text())
    for model, record in catalogue['serving_verification'].items():
        run_id = record.get('probe_run_id', latest)
        record.update(probe_run_id=run_id, evidence_ids=model_ids[(model, run_id)])
    path.write_text(json.dumps(catalogue, indent=2) + '\n')
    (sample / 'hosted_probe_world_events.jsonl').write_text(''.join(json.dumps({'world_event': e}, ensure_ascii=False) + '\n' for e in events))
    for stream in ('llm_calls', 'llm_errors', 'zetaris_queries'):
        path = Path('logs') / (stream + '.jsonl')
        selected = [r for line in path.read_text().splitlines() if (r := json.loads(line))['run_id'] in run_ids]
        (sample / ('hosted_probe_audit_' + stream + '.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected))
    print(f'Archived {len(events)} serving observations and raw attempts from {len(run_ids)} diagnostic runs.')


if __name__ == '__main__':
    main()
