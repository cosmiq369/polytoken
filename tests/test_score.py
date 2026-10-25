"""Offline evaluator regressions: recorded outcomes, ordering and fail-closed replay."""
import copy
import json
from pathlib import Path

import pytest

from polytoken.billing_view import archived_events, BillingUnavailable
from polytoken.logs import JsonlLogger
from polytoken.score import evaluate, latest_complete

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def score_source():
    report = json.loads((ROOT/'logs/sample/agent_samudra_v3_report.json').read_text())
    return report, archived_events(ROOT/'logs')


def test_recorded_quality_floor_blocks_recommendation(score_source, tmp_path):
    report, records = score_source
    result = evaluate(report, records, JsonlLogger(tmp_path))
    assert result['top_finding']['status'] == 'pass'
    assert result['expected_fix']['status'] == 'inconclusive'
    assert result['expected_fix']['contract_ab_verdict'] == 'fail'
    assert result['expected_fix']['aa'] == {'passed': 7, 'judged': 20}
    assert result['expected_fix']['ab'] == {'passed': 3, 'judged': 20}
    assert result['diagnostics']['byte_identical'] == 3
    assert result['diagnostics']['added_only_different'] == 11
    assert all(row['respected'] for row in result['limits'].values())
    assert result['questions']['3']['status'] == 'partly'


def test_score_rejects_forged_pass_and_missing_source(score_source, tmp_path):
    report, records = score_source
    forged = copy.deepcopy(report)
    next(c for c in forged['claims'] if c['id']=='quality/passed')['value'] = 20
    with pytest.raises(ValueError, match='failed evidence replay'):
        evaluate(forged, records, JsonlLogger(tmp_path))
    with pytest.raises(BillingUnavailable):
        latest_complete([(Path('latest.json'), report)], [])


def test_complete_selection_uses_evidence_time_not_filename(score_source):
    report, records = score_source
    older = json.loads((ROOT/'logs/sample/agent_samudra_v3_951bc9dc-c21d-424f-aebd-696df0ebdcd7_report.json').read_text())
    partial = {**report, 'id': 'partial-newer', 'status': 'partial'}
    chosen = latest_complete([(Path('zzz.json'), older), (Path('aaa.json'), report), (Path('new.json'), partial)], records)
    assert chosen['samudra'][1]['id'] == report['id']
