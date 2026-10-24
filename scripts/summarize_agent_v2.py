#!/usr/bin/env python3
"""Render the checkpoint summary from checked reports and verified probe records."""
import json
from pathlib import Path
import subprocess

SAMPLE = Path('logs/sample')


def number(value, digits=2):
    return 'unavailable' if value is None else f'{value:,.{digits}f}'


def main():
    reports = [json.loads((SAMPLE / f'agent_{company}_v2_report.json').read_text()) for company in ('samudra', 'swara')]
    assert all(r['status'] != 'running' and all(c['verified'] for c in r['claims']) for r in reports)
    catalogue = json.loads(Path('data/reference/nvidia_hosted.json').read_text())
    out = ['# PROMPT-04B completion report — 24 October 2026', '',
           'The company runs used Zetaris and the one injected NVIDIA generator. Hosted work ran after the checked reasoning report, with its own deadline. All earlier PROMPT-04 samples remain unchanged. Native review is still pending.', '',
           '## Commits and checks', '', 'Implementation commits on `feat/agent`:', '']
    out.extend('- `' + line.split(' ', 1)[0] + '` ' + line.split(' ', 1)[1] for line in subprocess.check_output(['git', 'log', '--reverse', '--format=%h %s', '5e7e5ca..HEAD'], text=True).splitlines())
    validation = [json.loads(line) for line in (SAMPLE / 'agent_v2_validation.jsonl').read_text().splitlines()]
    latest_tests = {row['command']: row for row in validation if row['event'] == 'test_result'}
    out.append('')
    for command, row in latest_tests.items():
        detail = f"{row['passed']} passed"
        if 'skipped' in row:
            detail += f"; {row['skipped']} skipped"
        if 'deselected' in row:
            detail += f"; {row['deselected']} deselected"
        out.append(f"- `{command}` — **{detail}**, {row['duration_s']:.2f} s.")
    replay = next(row for row in reversed(validation) if row['event'] == 'report_replay')
    out.append(f"- `{replay['command']}` — **{replay['accepted']} claims verified; {replay['dropped']} additional drops** across {replay['reports']} retained runs.")
    out.extend(['', 'Validation results are recorded in [agent_v2_validation.jsonl](agent_v2_validation.jsonl).', '',
                '## Serving probe', '',
                'Each row represents three short trials and three trials with Samudra’s full Telugu system prompt and one chat. TTFT is the median of successful visible-answer trials; failed or empty answers are never filled in. Every 404 was also tried without a system-role message.', '',
                '| Model | Usable | Short successes / TTFT (s) | Full Telugu successes / TTFT (s) |',
                '| --- | --- | --- | --- |'])
    for model, row in catalogue['serving_verification'].items():
        short, long = row['probe']['short'], row['probe']['long']
        out.append(f"| {model} | {'yes' if row['served'] else 'no'} | {short['ok']}/3; {number(short['ttft_median_s'])} | {long['ok']}/3; {number(long['ttft_median_s'])} |")
    probe_rows = [json.loads(line) for line in (SAMPLE / 'hosted_probe.jsonl').read_text().splitlines()]
    defaults = [r for r in probe_rows if r['model'] == 'openai/gpt-oss-20b' and not r['query'].get('reasoning_effort') and not r['no_system']]
    from statistics import median
    short = [r for r in defaults if r['variant'] == 'short']
    long = [r for r in defaults if r['variant'] == 'long']
    default_note = f"The completed GPT-OSS default-effort matrix had {sum(r['ok'] for r in short)}/{len(short)} short successes (median TTFT {number(median(r['ttft_s'] for r in short if r['ok']))} s) and {sum(r['ok'] for r in long)}/{len(long)} long successes."
    out.extend(['', 'Both Llama endpoints timed out in the completed matrix. Both Gemma endpoints returned 404, including all retries without a system role. GPT-OSS is the only admitted family and uses the separately probed `reasoning_effort=low` setting. A cross-family model switch was therefore unavailable. Both companies used a disclosed GPT-OSS stand-in; their deployed tokenizers and quoted prices still determine the cost scenarios.', '',
                default_note + ' The table above shows the follow-up low-effort matrix. All observations, including failures, are retained in [hosted_probe.jsonl](hosted_probe.jsonl), with content-addressed evidence in [hosted_probe_world_events.jsonl](hosted_probe_world_events.jsonl).', '',
                '## Company outcomes', '',
                '| Company | Status | Reasoning (s) | Job (s) | Nemotron / hosted / SQL attempts | Complete pairs | Same facts / judged | Dropped claims | Signed Markovian tokens / percent |',
                '| --- | --- | ---: | ---: | --- | --- | --- | ---: | --- |'])
    for report in reports:
        v = {c['id']: c['value'] for c in report['claims']}
        p = report['markovian_runs'][-1]['claim_prefix']
        out.append(f"| {report['company']} | {report['status']} | {number(v.get('budget/duration_s'))} | {number(v.get('jobs/duration_s'))} | {v.get('jobs/nemotron')} / {v.get('jobs/hosted')} / {v.get('jobs/sql')} | {v.get('experiment/completed_pairs')}/20 | {v.get('quality/passed')}/{v.get('quality/judged')} | {len(report['dropped_claims'])} | {v[p+'net_tokens']:+,} / {v[p+'net_percent']:+.2f}% |")
    out.extend(['', 'Call counts are physical attempts, including retries, across reasoning and jobs. Job duration includes generation, judging and speed trials. Markovian savings are signed reference history-replay counterfactuals for the reasoning chunks, not a second measured execution; deferred judge and hosted usage are separately audited.', ''])
    prior_runs = [json.loads(p.read_text()) for p in sorted(SAMPLE.glob('agent_swara_v2_*_report.json'))]
    if prior_runs:
        out.extend(['### Retained Swara attempt before cache recovery', ''])
        for prior in prior_runs:
            values = {c['id']: c['value'] for c in prior['claims']}
            prefix = prior['markovian_runs'][-1]['claim_prefix']
            out.append(f"- `{prior['id']}`: reasoning {number(values.get('budget/duration_s'))} s; job {number(values.get('jobs/duration_s'))} s; Nemotron/hosted/SQL {values.get('jobs/nemotron')}/{values.get('jobs/hosted')}/{values.get('jobs/sql')}; {values.get('experiment/completed_pairs')}/20 complete pairs; {prior['quality_status']}; stop reason {prior['partial_reason']}; {len(prior['dropped_claims'])} dropped claims; signed Markovian {values[prefix+'net_tokens']:+,} tokens ({values[prefix+'net_percent']:+.2f}%).")
        all_swara = [*prior_runs, reports[1]]
        totals = {k: sum(next(c['value'] for c in r['claims'] if c['id'] == 'jobs/' + k) for r in all_swara) for k in ('nemotron', 'hosted', 'sql')}
        out.extend(['', f"Across the retained Swara attempts, physical Nemotron/hosted/SQL totals are {totals['nemotron']}/{totals['hosted']}/{totals['sql']}. The final-run table counts only newly dispatched attempts; reused evidence is not counted as a new call.", ''])
    for report in reports:
        v = {c['id']: c['value'] for c in report['claims']}
        out.extend([f"### {report['company'].title()}", '', f"- Run: `{report['id']}`.",
            f"- Agent top finding, verbatim: **{report['top_finding']}**",
            f"- Agent top fix: **{report['top_fix'] or 'none'}**. Tested lever: `{report['experiment']['lever']}`.",
            f"- Whole-chat quoted content-cost scenario: **INR {number(v.get('experiment/original_monthly_inr'))}/month before → INR {number(v.get('experiment/changed_monthly_inr'))}/month after**.",
            f"- Quality verdict: **{report['quality_status']}**; {v.get('quality/passed')} same-facts passes among {v.get('quality/judged')} judged pairs. Eighteen of twenty are required; native review remains pending.",
            f"- Generated output length: {number(v.get('experiment/original_output_tokens'), 0)} → {number(v.get('experiment/changed_output_tokens'), 0)} measured tokens across twenty pairs; ratio {number(v.get('experiment/output_tokens_ratio'), 4)}. This is reported separately from the historical bill.",
            f"- Speed verdict: **{report['speed_status']}**. Throughput: {report.get('throughput_status', 'unavailable')}.",
            f"- Partial reason: {report['partial_reason'] or 'none'}.",
            f"- [Checked report](agent_{report['company']}_v2_report.json) · [Events](agent_{report['company']}_v2.jsonl)", ''])
    out.extend(['The after amounts are deterministic scenarios, not promised savings. For prompt levers, the historical completed requests, historical replies and replay remain fixed; only measured changed-system tokens are substituted, including added instructions. Generated reply-length differences are not inserted into this bill. A quality failure prevents an accepted fix regardless of the scenario saving.', '',
                '## Speed medians and spread', '',
                'Values are median [minimum, maximum], seconds; four trials per variant, ABBA twice. Spread and paired differences govern the verdict, not a favorable median alone.', '',
                '| Company / metric | Original | Changed | Paired difference median [min, max] |',
                '| --- | --- | --- | --- |'])
    for report in reports:
        v = {c['id']: c['value'] for c in report['claims']}
        for metric in ('ttft_s', 'latency_s'):
            p = 'speed/' + metric + '/'
            def spread(variant):
                return f"{number(v.get(p+variant+'_median'))} [{number(v.get(p+variant+'_min'))}, {number(v.get(p+variant+'_max'))}]"
            diff = f"{number(v.get(p+'paired_difference'))} [{number(v.get(p+'difference_min'))}, {number(v.get(p+'difference_max'))}]"
            out.append(f"| {report['company']} / {metric} | {spread('original')} | {spread('changed')} | {diff} |")
    out.extend(['', '## Deviations and limitations', '',
        '1. Two initial probe launches were interrupted after result serialization errors. Their completed raw call/error logs and partial observations are retained; interrupted in-flight outcomes are unknown. The complete matrix was rerun after testing the recorder. No observations from those incomplete launches determined model eligibility.',
        '2. Llama 11B answered in the aborted diagnostics but timed out on all six trials of the completed matrix. It was excluded rather than assumed available from earlier success. Gemma remained 404 with and without system roles.',
        '3. GPT-OSS default effort produced no usable full-Telugu answer in the completed matrix, so a documented low-effort follow-up was run without raising the 200-token cap. [NVIDIA documents this option](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b-infer). Original and follow-up measurements are both retained.',
        '4. Only GPT-OSS passed the completed serving probes, so neither run could test an actual cross-family model switch. Stand-in results do not establish deployed-model quality or latency.',
        '5. Jobs are queued by the reasoning loop and executed by the API/CLI worker after publishing the initial checked report. The four-worker generation pool is separate from the six-minute reasoning allowance. Speed trials preserve the sequential ABBA protocol. CLI waits for completion; restart recovery requires a rerun, which reuses successful evidence.',
        '6. Samudra was already running when unseparated reasoning usage was identified. Its completed report was reverified offline from the same evidence, dropping nine unsupported throughput claims without network calls. The original report remains in `agent_samudra_v2_report_before_throughput_correction.json`. Swara uses the corrected throughput logic directly. TTFT and total latency are retained.',
        '7. Swara’s first planner stopped reasoning early after queuing its job; the early-stop reason remains in the initial running-report audit. One changed reply exhausted its retries, leaving 19 pairs and an insufficient-sample verdict with no judge calls. The first job reached its thirty-minute boundary (with the two-second finalization reserve), retaining six valid speed trials. One bounded recovery investigation was requested for the same answer_cap lever, reusing 39 successful generation calls and six speed trials while retrying the one missing reply and two missing speed trials. The initial attempt is retained; this was not a contract or threshold change.',
        '8. Native spot checks have not been performed. Automated quality failure and insufficient sample remain distinct. Cost projections exclude chat-template overhead, retries and unpublished cache discounts.',
        '9. The requested claude-mem work-state tools were unavailable, and memory capture initially reported a quota cooldown. The worker was not restarted. The chat’s model/effort settings were not changed by the prompt header; no subagents were used.',
        '10. Sandbox escalation was required for local service access, NVIDIA calls, and Git metadata/push. Automatic approval review initially rejected the push because the destination and company-data provenance were unverified. Read-only GitHub checks confirmed the authenticated owner’s private repository and ADMIN permission; all three snapshot texts exactly matched the declared fictional fixtures, and the secret scan passed. These checks are recorded before retrying the upload. No secrets were committed. The contract received only the required dated pre-run addendum; it was not adjusted during either company rerun.', '',
        '## Evidence archive', '',
        '- `agent_samudra_v2.jsonl`, `agent_swara_v2.jsonl` and their checked reports.',
        '- `agent_v2_world_events.jsonl`: complete transitive evidence closure for replay.',
        '- `agent_v2_audit_*.jsonl`: all model attempts, errors, SQL, planner decisions, native review, Markovian, cache and checker records for these runs.',
        '- `hosted_probe*.jsonl`: every retained serving diagnostic and archived probe evidence.',
        '- `agent_v2_validation.jsonl`: exact validation commands, results, evidence checks and the throughput correction.', '',
        'Stopped at the PROMPT-04B checkpoint; no UI, native review, contract scoring, tags or release was started.', ''])
    (SAMPLE / 'agent_v2_completion_report.md').write_text('\n'.join(out))


if __name__ == '__main__':
    main()
