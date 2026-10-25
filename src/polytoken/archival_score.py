"""Offline contract evaluation. Never imported by the investigation or its tools."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .billing_view import EventWorld, archived_events, build_billing
from .checker import Checker
from .logs import JsonlLogger

EXPECTED = {'samudra': ('system_prompt', 'english_system'), 'swara': ('output', 'answer_cap')}
LIMITS = {'nemotron': 25, 'judge': 45, 'hosted': 70, 'sql': 60}


def latest_complete(reports, records):
    """Order by the authenticated reasoning telemetry timestamp, never filenames."""
    world = EventWorld(records)
    selected = {}
    for path, report in reports:
        if report.get('status') != 'complete' or report.get('company') not in EXPECTED:
            continue
        budget = next((c for c in report['claims'] if c['id'] == 'budget/duration_s'), None)
        if not budget:
            continue
        eid = budget['recompute']['inputs']['budget']
        world.verify(eid)
        stamp = world.records[eid]['provenance']['fetched_at']
        moment = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        company = report['company']
        if company not in selected or (moment, report['id']) > selected[company][0]:
            selected[company] = ((moment, report['id']), path, report)
    return {c: (path, report) for c, (_, path, report) in selected.items()}


def diagnostics(experiment, quality):
    """Counts over authenticated generations and checker-validated inventories."""
    pairs = experiment.get('pairs', [])
    available = [p for p in pairs if all(p.get(v, {}).get('ok') and p[v].get('finish_reason') == 'stop'
                                         for v in ('original', 'control'))]
    identical = [p['chat_id'] for p in available if p['original']['text'].encode('utf-8') == p['control']['text'].encode('utf-8')]
    added_only, different = [], []
    from .agent.quality import validate_claims
    for row in quality.get('pairs', []):
        if row.get('same_facts') is None:
            continue
        same = validate_claims(row, {'chat_id': row['chat_id'], **row['reply_texts']})
        if same:
            continue
        different.append(row['chat_id'])
        statuses = {c['status'] for side in ('original', 'changed') for c in row[side + '_claims']
                    if c['material'] and c['status'] != 'present'}
        if statuses == {'added'}:
            added_only.append(row['chat_id'])
    return dict(aa_pairs=len(available), byte_identical=len(identical), byte_identical_chat_ids=identical,
                different_verdicts=len(different), added_only_different=len(added_only), added_only_chat_ids=added_only)


def evaluate(report, records, logger):
    world = EventWorld(records)
    checked, dropped = Checker(SimpleNamespace(world=world), logger).check(report['claims'])
    if dropped:
        raise ValueError(f"{report['id']}: {len(dropped)} claims failed evidence replay")
    values = {c['id']: c['value'] for c in checked}
    billing = build_billing(report, records, logger=logger)
    spec = billing['tokenizer']
    prefix = f'baseline/{spec}/'
    component, lever = EXPECTED[report['company']]
    shares = {part: values.get(prefix + part + '_cost_share') for part in ('system_prompt', 'user', 'assistant', 'output')}
    measured = {k: v for k, v in shares.items() if v is not None}
    top = max(measured, key=measured.get) if measured else None
    # The expected label must occur in the agent's own emitted finding, supported by its own checked shares.
    finding_pass = top == component and component in (report.get('top_finding') or '')
    def question(status, ids, reason):
        return dict(status=status, claim_ids=ids, reason=reason)
    ratios = [c['id'] for c in checked if c['id'].startswith('ratios/')]
    money = [c['id'] for c in checked if c['id'].startswith('baseline/') and c['id'].endswith('/monthly_inr')]
    parts = [c['id'] for c in checked if c['id'].startswith(prefix) and c['id'].endswith(('_tokens', '_cost_share'))]
    timing = [c['id'] for c in checked if c['id'].startswith('speed/')]
    fixes = [f['claim_id'] for f in report.get('fixes', []) if f['claim_id'] in values]
    questions = {
        '1': question('partly' if ratios and money else 'no', ratios + money,
                      'Paired token ratios and chat bootstrap bounds cover the measured models; priced models have checked billing. Missing model prices and cost-ratio intervals prevent a complete cost answer for every model.'),
        '2': question('yes' if all(p in measured for p in ('system_prompt', 'user', 'assistant', 'output')) else 'partly' if parts else 'no', parts,
                      'Checked attribution separates system instructions, users, replayed answers and new output.'),
        '3': question('partly' if any('/latency_s/' in k for k in timing) else 'no', timing,
                      'Hosted original/changed timing is measured. This is not a paired native/English reply-speed experiment on the deployed model; inseparable reasoning usage prevents output-throughput claims.'),
        '4': question('partly' if fixes else 'no', fixes + [k for k in values if k.startswith('quality/')],
                      'Alternatives are ranked by checked monthly saving. No fix has demonstrated the contract quality bar plus native review; uncertainty is retained.')}
    expected_fix = next((f for f in report.get('fixes', []) if f['lever'] == lever), {})
    aa = dict(passed=values.get('quality/aa/passed'), judged=values.get('quality/aa/judged'))
    ab = dict(passed=values.get('quality/passed'), judged=values.get('quality/judged'))
    tested_expected = report.get('experiment', {}).get('lever') == lever if report.get('experiment') else False
    native = report.get('review_status', 'not recorded')
    inconclusive = (not tested_expected or aa['judged'] != 20 or (aa['passed'] or 0) < 18 or ab['judged'] != 20)
    verdict = 'inconclusive' if inconclusive else 'rejected' if (ab['passed'] or 0) < 18 or native == 'rejected' else 'recommended' if native == 'approved' else 'inconclusive'
    final_prefix = 'jobs/' if 'jobs/nemotron' in values else 'budget/'
    limits = {key: dict(actual=values.get(final_prefix+key), maximum=cap, claim_id=final_prefix+key)
              for key, cap in LIMITS.items()}
    limits.update(reasoning_seconds=dict(actual=values.get('budget/duration_s'), maximum=360, claim_id='budget/duration_s'),
                  job_seconds=dict(actual=values.get('jobs/duration_s'), maximum=1800, claim_id='jobs/duration_s'))
    for row in limits.values():
        row['respected'] = row['actual'] <= row['maximum'] if row['actual'] is not None else None
    raw_experiment = world.verify(report['experiment']['evidence_ids'][0]) if report.get('experiment') else {}
    control_ids = report.get('control_quality_evidence_ids', [])
    control = world.verify(control_ids[0]) if control_ids else {}
    diagnostic = diagnostics(raw_experiment, control)
    logger.write('contract_score', 'diagnostics_recomputed', report_id=report['id'], diagnostics=diagnostic,
                 evidence_ids=(report.get('experiment') or {}).get('evidence_ids', []) + control_ids)
    return dict(company=report['company'], run_id=report['id'], questions=questions,
                top_finding=dict(status='pass' if finding_pass else 'fail', expected=component, actual=top,
                                 agent_finding=report.get('top_finding'), claim_ids=[prefix+p+'_cost_share' for p in measured]),
                expected_fix=dict(lever=lever, status=verdict, agent_status=expected_fix.get('status', 'not investigated'),
                                  tested=tested_expected, aa=aa, ab=ab, native_review=native,
                                  contract_ab_verdict='pass' if ab['judged']==20 and ab['passed']>=18 else 'fail' if ab['judged']==20 else 'insufficient sample',
                                  interpretation=report.get('quality_interpretation'), claim_ids=[k for k in values if k.startswith('quality/')]),
                limits=limits, diagnostics=diagnostic, verified_claims=len(checked),
                diagnostic_evidence_ids=(report.get('experiment') or {}).get('evidence_ids', []) + control_ids,
                billing_claims=billing['headline'])


def score(sample_dir='logs/sample', output=None):
    sample = Path(sample_dir)
    output = Path(output) if output else sample / 'contract_score'
    records = archived_events(sample.parent)
    reports = [(p, json.loads(p.read_text())) for p in sorted(sample.glob('*_report.json'))]
    chosen = latest_complete(reports, records)
    logger = JsonlLogger(sample.parent, run_id='offline-contract-score')
    rows = []
    for company in EXPECTED:
        if company not in chosen:
            rows.append(dict(company=company, status='no complete run'))
            continue
        path, report = chosen[company]
        row = evaluate(report, records, logger)
        row['report_file'] = str(path)
        row['report_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        row['contract_file'] = 'docs/CONTRACT.md'
        row['contract_sha256'] = hashlib.sha256(Path('docs/CONTRACT.md').read_bytes()).hexdigest()
        rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    lines = ['# Offline pre-registered contract score', '',
             'Computed from the latest complete run per company, ordered by authenticated reasoning telemetry. The agent never imports this evaluator. Scores are not inputs to the investigation.', '',
             '| Company | Q1 cost | Q2 source | Q3 speed | Q4 fixes | Top finding | Expected fix | A/A | A/B | Native review |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in rows:
        if 'questions' not in r:
            lines.append(f"| {r['company']} | no complete run | | | | | | | | |")
            continue
        f = r['expected_fix']
        lines.append('| ' + ' | '.join([r['company'], *[r['questions'][str(i)]['status'] for i in range(1,5)], r['top_finding']['status'], f['status'], f"{f['aa']['passed']}/{f['aa']['judged']}", f"{f['ab']['passed']}/{f['ab']['judged']}", f['native_review']]) + ' |')
    for r in rows:
        if 'questions' not in r:
            continue
        f, d = r['expected_fix'], r['diagnostics']
        lines += ['', f"## {r['company'].title()}", '', f"Run `{r['run_id']}` · [{Path(r['report_file']).name}]({Path(r['report_file']).name}) · {r['verified_claims']} claims replayed.", '',
                  f"Agent finding: {r['top_finding']['agent_finding']}",
                  f"Expected fix: `{f['lever']}`; agent status: {f['agent_status']}. Literal 18/20 A/B contract verdict: **{f['contract_ab_verdict']}**.",
                  f"Interpretation: **{f['interpretation']}**. Native review: {f['native_review']}.", '',
                  f"A/A: **{d['byte_identical']}/{d['aa_pairs']}** reply pairs are byte-identical. Of **{d['different_verdicts']}** different verdicts, **{d['added_only_different']}** contain only added material claims. These are model classifications, not human ground truth; both variation and strictness may contribute.", '',
                  '| Limit | Actual | Maximum | Respected |', '| --- | ---: | ---: | --- |']
        for key, v in r['limits'].items():
            lines.append(f"| {key} | {v['actual']} | {v['maximum']} | {'yes' if v['respected'] else 'no' if v['respected'] is False else 'not measured'} |")
        for q, data in r['questions'].items():
            lines += ['', f"### Question {q}: {data['status']}", '', data['reason'], '', 'Claim IDs: ' + ', '.join('`'+k+'`' for k in data['claim_ids']) + '.']
        lines += ['', 'Diagnostic evidence IDs: ' + ', '.join('`'+k+'`' for k in r['diagnostic_evidence_ids']) + '.',
                  '', 'Full recipes, source hashes, limits and exact diagnostic chat IDs are in [contract_score.jsonl](contract_score.jsonl).']
    output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    return rows
