#!/usr/bin/env python3
"""Offline replay from curated World Model events, without services or hidden fixtures."""
import argparse
import json
from pathlib import Path

from polytoken.checker import Checker
from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.world_model import WorldModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+')
    parser.add_argument('--evidence', default='logs/sample/agent_world_events.jsonl')
    args = parser.parse_args()
    logger = JsonlLogger()
    with WorldModel(storage='memory', logger=logger) as world:
        for line in Path(args.evidence).read_text().splitlines():
            event = json.loads(line)['world_event']
            world.db.execute('INSERT OR IGNORE INTO events(event_id,kind,item_key,payload,provenance,at) VALUES(?,?,?,?,?,?)',
                             (event['event_id'], event['kind'], event['item_key'], json.dumps(event['payload']),
                              json.dumps(event['provenance']), event['at']))
        world.db.commit()
        checker = Checker(EvidenceStore(world), logger)
        failures = 0
        for path in args.reports:
            report = json.loads(Path(path).read_text())
            passed, dropped = checker.check(report['claims'])
            print(f"{report['id']}: {len(passed)} verified; {len(dropped)} dropped on replay")
            logger.write('agent_replay', 'verified_report', report=path, accepted=len(passed), dropped=dropped, ok=not dropped)
            failures += len(dropped)
        return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
