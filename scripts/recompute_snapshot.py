"""Check an archived Zetaris snapshot without changing its original evidence."""
import argparse
from pathlib import Path
from polytoken.company_db import jsonl
from polytoken.logs import JsonlLogger
from polytoken.measurement_report import billed_shares, bootstrap_ratios


def recompute(path):
    snapshot = jsonl(path)
    inputs = [i for s in snapshot for i in s['inputs']]
    counts = [c for s in snapshot for c in s['counts']]
    sample = JsonlLogger(path.parent)
    provenance = dict(source='Archived verified Zetaris SQL snapshot',query=[s['query'] for s in snapshot],
                      fetched_at=[s['fetched_at'] for s in snapshot],time_window=[s['time_window'] for s in snapshot],
                      measurement_run_ids=sorted({c['run_id'] for c in counts}),ok=True,
                      translation_review='pending',money_available=False)
    sample.write('planted_properties','verified_token_shares',rows=billed_shares(inputs,counts),**provenance)
    sample.write('bootstrap','verified_cluster_intervals',rows=bootstrap_ratios(inputs,counts),**provenance)
    print('Verified archived shares and intervals:',len(counts),'measurements')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot',type=Path)
    recompute(parser.parse_args().snapshot)
