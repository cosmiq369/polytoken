#!/usr/bin/env python3
"""Archive every completed agent run and its complete replayable evidence closure."""
import argparse
import gzip
import json
from pathlib import Path

from polytoken.logs import JsonlLogger
from polytoken.meterless.world_model import WorldModel


def archive(path, rows):
    content = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode('utf-8')
    if len(content) > 5_000_000:
        if path.exists():
            raise ValueError('Preserve existing evidence; use a fresh archive prefix')
        path.with_suffix(path.suffix + '.gz').write_bytes(gzip.compress(content, mtime=0))
    else:
        path.write_bytes(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-glob', default='agent_*report.json')
    parser.add_argument('--prefix', default='agent')
    args = parser.parse_args()
    if not args.prefix.replace('_', '').isalnum():
        parser.error('prefix must contain only letters, digits and underscores')
    sample = Path('logs/sample')
    reports = [json.loads(p.read_text()) for p in sorted(sample.glob(args.report_glob))]
    if not reports:
        parser.error('no matching reports')
    run_ids = {r['id'] for r in reports}
    wanted = {eid for r in reports for eid in r.get('evidence_ids', [])}
    validation = sample / 'agent_validation.jsonl'
    if validation.exists() and args.prefix == 'agent':
        wanted.update(row['evidence_id'] for line in validation.read_text().splitlines()
                      if (row := json.loads(line)).get('event') == 'hosted_diagnostic' and row.get('evidence_id'))
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
    archive(sample / (args.prefix + '_world_events.jsonl'), rows)
    streams = ('llm_calls', 'llm_errors', 'zetaris_queries', 'planner', 'native_review', 'agent_markovian', 'checker', 'hmem', 'agent', 'experiment_jobs', 'quality', 'model_fit')
    for stream in streams:
        source = Path('logs') / (stream + '.jsonl')
        if not source.exists():
            continue
        selected = [row for line in source.read_text().splitlines() if (row := json.loads(line)).get('run_id') in run_ids]
        if selected:
            archive(sample / (args.prefix + '_audit_' + stream + '.jsonl'), selected)
    print(f'Curated {len(run_ids)} runs and {len(rows)} World Model events; no best-run filtering.')


if __name__ == '__main__':
    main()
