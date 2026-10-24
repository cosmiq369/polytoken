#!/usr/bin/env python3
"""Archive every completed agent run and its complete replayable evidence closure."""
import json
from pathlib import Path

from polytoken.logs import JsonlLogger
from polytoken.meterless.world_model import WorldModel


def main():
    sample = Path('logs/sample')
    reports = [json.loads(p.read_text()) for p in sorted(sample.glob('agent_*report.json'))]
    run_ids = {r['id'] for r in reports}
    wanted = {eid for r in reports for eid in r.get('evidence_ids', [])}
    with WorldModel(logger=JsonlLogger()) as world:
        events = {event['event_id']: event for event in world.events()}
    pending = list(wanted)
    while pending:
        eid = pending.pop()
        for parent in events[eid]['payload'].get('supports', []):
            if parent not in wanted:
                wanted.add(parent)
                pending.append(parent)
    rows = [{'world_event': event} for eid, event in events.items() if eid in wanted]
    (sample / 'agent_world_events.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    streams = ('llm_calls', 'llm_errors', 'zetaris_queries', 'planner', 'native_review', 'agent_markovian', 'checker', 'hmem', 'agent')
    for stream in streams:
        source = Path('logs') / (stream + '.jsonl')
        if not source.exists():
            continue
        selected = [row for line in source.read_text().splitlines() if (row := json.loads(line)).get('run_id') in run_ids]
        (sample / ('agent_audit_' + stream + '.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in selected))
    print(f'Curated {len(run_ids)} runs and {len(rows)} World Model events; no best-run filtering.')


if __name__ == '__main__':
    main()
