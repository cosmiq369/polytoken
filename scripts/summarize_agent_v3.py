#!/usr/bin/env python3
"""Build the v3 checkpoint and fixed-seed native review from checked evidence."""
import html
import json
from pathlib import Path
import random

from polytoken.checker import Checker
from polytoken.logs import JsonlLogger
from polytoken.meterless.evidence import EvidenceStore
from polytoken.meterless.world_model import WorldModel
from polytoken.agent.quality import SEED

SAMPLE = Path('logs/sample')


def cell(text):
    return html.escape(str(text)).replace('|', '&#124;').replace('\n', '<br>')


def main():
    logger = JsonlLogger(SAMPLE, run_id='prompt04c-summary')
    with WorldModel(storage='memory', logger=logger) as world:
        for line in (SAMPLE / 'agent_v3_world_events.jsonl').read_text().splitlines():
            e = json.loads(line)['world_event']
            world.db.execute('INSERT OR IGNORE INTO events(event_id,kind,item_key,payload,provenance,at) VALUES(?,?,?,?,?,?)',
                             (e['event_id'], e['kind'], e['item_key'], json.dumps(e['payload']), json.dumps(e['provenance']), e['at']))
        world.db.commit()
        events = {e['event_id']: e['payload'] for e in world.events()}
        checker = Checker(EvidenceStore(world), JsonlLogger(run_id='prompt04c-summary'))
        history = {}
        for path in sorted(SAMPLE.glob('agent_*v3*report.json')):
            retained = json.loads(path.read_text())
            checked, dropped = checker.check(retained['claims'])
            if dropped:
                raise ValueError(f'{path}: {dropped}')
            history[retained['id']] = (path, retained, {c['id']: c['value'] for c in checked})
        lines = ['# PROMPT-04C completion report — 25 October 2026', '',
                 'Contextual A/A and A/B experiments on the declared fictional companies. The contract threshold remains 18/20; native review remains pending. Every previous run and score is retained.', '',
                 '## Company outcomes', '',
                 '| Company | A/A same facts | A/B same facts | Excluded chats (truncated) | Contract verdict | Monthly INR before → after | Speed |',
                 '| --- | --- | --- | --- | --- | --- | --- |']
        results = {}
        for company in ('samudra', 'swara'):
            report = json.loads((SAMPLE / f'agent_{company}_v3_report.json').read_text())
            checked, dropped = checker.check(report['claims'])
            if dropped:
                raise ValueError(f'{company}: {dropped}')
            v = {c['id']: c['value'] for c in checked}
            experiment = events[report['experiment']['evidence_ids'][0]] if report.get('experiment') else None
            results[company] = report, v, experiment
            score = lambda prefix: f"{v.get(prefix + '/passed', 0)}/{v.get(prefix + '/judged', 0)} judged (target 20)"
            money = lambda variant: f"{v['experiment/' + variant + '_monthly_inr']:,.2f}" if 'experiment/' + variant + '_monthly_inr' in v else 'unavailable'
            lines.append(f"| {company} | {score('quality/aa')} | {score('quality')} | {v.get('experiment/exclusions', 'unavailable')} ({v.get('experiment/truncation_exclusions', 'unavailable')}) | {report['quality_status']} | {money('original')} → {money('changed')} | {report['speed_status']} |")
        for company, (report, v, experiment) in results.items():
            lines += ['', f'### {company.title()}', '', f"- Run: `{report['id']}`; status: {report['status']}; partial reason: {report.get('partial_reason') or 'none'}.",
                      f"- Lever: `{experiment['lever'] if experiment else 'none'}`; top fix: {report['top_fix'] or 'none'}.",
                      f"- Interpretation: **{report.get('quality_interpretation') or 'No quality result available.'}**",
                      f"- Top finding: {report['top_finding']}",
                      f"- Model: {(experiment or {}).get('models', {})}; {(experiment or {}).get('model_label', '')}.",
                      f"- Throughput: {report['throughput_status']}.",
                      f"- Reused validated judgments: A/A {v.get('quality/aa/cache_hits', 0)}, A/B {v.get('quality/cache_hits', 0)}. Exact model, comparison, full policy/history/replies and judge format must match; accepted judgments are not resampled.",
                      f"- [Checked report](agent_{company}_v3_report.json) · [Events](agent_{company}_v3.jsonl)", '',
                      '| Comparison | Missing material claims | Contradicted material claims | Added material claims |',
                      '| --- | ---: | ---: | ---: |']
            for label, prefix in [('A/A', 'quality/aa'), ('A/B', 'quality')]:
                lines.append('| ' + label + ' | ' + ' | '.join(str(v.get(prefix + '/' + s, 'unavailable')) for s in ('missing', 'contradicted', 'added')) + ' |')
            lines += ['', 'Counts are inventory entries across both reply lists; a contradiction listed in both inventories counts twice. They are classifications by the model, not human factuality judgments.', '',
                      '| Timing metric | Original median [min, max] s | Changed median [min, max] s | Paired difference median [min, max] s |',
                      '| --- | --- | --- | --- |']
            for metric in ('ttft_s', 'latency_s'):
                def interval(variant):
                    prefix = f'speed/{metric}/'
                    keys = ([prefix + variant + '_' + suffix for suffix in ('median', 'min', 'max')] if variant != 'difference'
                            else [prefix + key for key in ('paired_difference', 'difference_min', 'difference_max')])
                    if not all(k in v for k in keys):
                        return 'unavailable'
                    return f'{v[keys[0]]:.2f} [{v[keys[1]]:.2f}, {v[keys[2]]:.2f}]'
                lines.append(f'| {metric} | {interval("original")} | {interval("changed")} | {interval("difference")} |')
            lines += ['', f"Latest investigation physical attempts: reasoning {v.get('jobs/nemotron', v.get('budget/nemotron'))}; judge {v.get('jobs/judge', 0)}; hosted {v.get('jobs/hosted', 0)}; SQL {v.get('jobs/sql', v.get('budget/sql'))}. Job time {v.get('jobs/duration_s', 0):.2f} s."]
            prior = [values for _, r, values in history.values() if r['company'] == company]
            total = {kind: sum(values.get('jobs/' + kind, values.get('budget/' + kind, 0)) for values in prior)
                     for kind in ('nemotron', 'judge', 'hosted', 'sql')}
            lines += ['', f"Across all {len(prior)} retained {company} investigations: reasoning {total['nemotron']}, judge {total['judge']}, hosted {total['hosted']}, SQL {total['sql']} physical attempts. Limits apply per investigation; recovery totals are not hidden behind the latest run's cache hits."]
            if experiment and experiment['excluded_pairs']:
                lines += ['', 'Excluded chats: ' + ', '.join(p['chat_id'] for p in experiment['excluded_pairs']) + '. Full failure rows and retry attempts remain in the World Model archive.']
        lines += ['', '## Prior scores and run history', '',
                  'V2 remains Samudra **1/20** and Swara **0/20**, with the original failed-quality verdicts and diagnosis unchanged. These used the earlier protocol and are not a controlled trend comparison with v3. See [v2 report](agent_v2_completion_report.md) and [quality diagnosis](agent_v2_quality_diagnosis.md).', '',
                  '| Company / retained v3 attempt | Status | A/A | A/B | Reasoning / judge / hosted / SQL attempts |', '| --- | --- | --- | --- | --- |']
        for path, r, values in history.values():
            score = lambda prefix: f"{values.get(prefix + '/passed', 0)}/{values.get(prefix + '/judged', 0)}"
            counts = ' / '.join(str(values.get('jobs/' + k, values.get('budget/' + k, 0))) for k in ('nemotron', 'judge', 'hosted', 'sql'))
            lines.append(f"| [{r['company']} / {r['id']}]({path.name}) | {r['status']} | {score('quality/aa')} | {score('quality')} | {counts} |")
        lines += ['', '## Validation', '']
        validation = {}
        for line in (SAMPLE / 'agent_v3_validation.jsonl').read_text().splitlines():
            entry = json.loads(line)
            if entry.get('event') in ('tests', 'final_tests', 'replay', 'commit'):
                key = entry.get('command', entry.get('commit', ''))
                validation[key] = entry
        for key, entry in validation.items():
            summary = entry.get('summary') or entry.get('result', 'recorded').strip().splitlines()[-1]
            lines.append(f"- `{key}` — {summary}")
        lines += ['', '## Interpretation, deviations and limitations', '',
                  '- Full history and policy now reach the generator/judge; GPT-OSS uses low reasoning effort and a 1024-token generation allowance. Completed answers require finish_reason=stop. One regeneration is allowed for length truncation. Selection is a fixed permutation, with exclusions before any judgments.',
                  '- A1 is shared across A/A and A/B, while A2 is independently generated. Separate replicate cache keys prevent copying the baseline into its control. Successful calls can be reused only under the same contextual protocol and settings.',
                  '- When a partial run exhausts its judge allowance, a bounded recovery reuses the first valid judgment for an exact model/comparison/full-prompt match and requests only missing verdicts. Cached raw calls remain evidence parents; all attempts and partial scores stay in history.',
                  '- Forty judgments require the pre-run addendum: 25 reasoning attempts plus 45 judge attempts. Hosted attempts remain capped at 70, SQL at 60, reasoning at six minutes and background work at thirty minutes per investigation. Any recovery runs are separately retained in the history table.',
                  '- Monthly amounts reconstruct the same historical whole-chat content bill, replacing measured system tokens only. Generated reply-length differences do not substitute for historical answers in the bill. These are quoted scenarios, not invoice totals.',
                  '- The first Samudra v3 judge format failed on malformed JSON and invented Telugu quotations. That attempt remains in history. A dated serialization addendum introduced numbered source excerpts: the judge cites IDs in English JSON, and code attaches the exact native text. Generation settings, selection and the quality bar are unchanged.',
                  '- Exact quote/schema validation and deterministic recomputation catch invented excerpts and arithmetic errors; they cannot establish whether every semantic classification is correct. Native review is pending and blocks final acceptance.',
                  '- The initial sandbox live checks could not access services. After escalation, one federation test lacked its reference-price HTTP service; starting that service resolved it. Automatic review initially rejected live generation as private-data export; exact comparison of all policy/chat fields against the fictional fixtures established synthetic provenance before retrying.',
                  '- The claude-mem work_state tools are absent from this session. Validation and protocol evidence are recorded in JSONL. The prompt header did not change the chat model/effort. No subagents were used.',
                  '- Prior samples remain unchanged. UI files and the static-file mount belong to PROMPT-05; this task adds only localhost CORS to the API.', '',
                  '## Mohan: native review requested', '',
                  'Please review the 10 fixed-seed Telugu pairs in [native_review_samudra.md](native_review_samudra.md), comparing the policy/history, both replies and judge claim inventories. Fill in same meaning / different meaning / unsure and a reason. Any different-meaning verdict blocks the fix. A Hindi reviewer must separately review ten Hindi pairs; this run does not claim that review occurred.', '',
                  'Evidence: [World Model closure](agent_v3_world_events.jsonl), `agent_v3_audit_*.jsonl`, and [validation](agent_v3_validation.jsonl). Stopped at PROMPT-04C.']
        (SAMPLE / 'agent_v3_completion_report.md').write_text('\n'.join(lines) + '\n')
        report, v, experiment = results['samudra']
        if experiment:
            quality = events[report['quality_evidence_ids'][0]]
            verdicts = {r['chat_id']: r for r in quality['pairs']}
            pairs = random.Random(SEED).sample(sorted(experiment['pairs'], key=lambda p: p['chat_id']), min(10, len(experiment['pairs'])))
            review = ['# Samudra Telugu native review — v3', '',
                      f"Run `{report['id']}`. Ten accepted A/B pairs selected without reference to judge outcome, seed {SEED}. No verdict has been filled in for Mohan.", '',
                      f"A/A: {v.get('quality/aa/passed', 0)}/{v.get('quality/aa/judged', 0)}; A/B: {v.get('quality/passed', 0)}/{v.get('quality/judged', 0)}. {report.get('quality_interpretation')}", '',
                      'Mohan: record **same meaning**, **different meaning**, or **unsure**, plus the material difference or judge error. Check unsupported baseline claims as well as omissions; a correction can differ without being worse. Any different-meaning verdict blocks the fix.', '',
                      '## Original company policy', '', experiment['systems']['original'], '', '## Changed system prompt', '', experiment['systems']['changed']]
            for pair in pairs:
                q = verdicts.get(pair['chat_id'], {})
                review += ['', f"## {pair['chat_id']}", '', '### Conversation through last user turn', '']
                review.extend(f"**{m['role']}:** {m['content']}\n" for m in pair['conversation'])
                review += ['', '| Original A1 | Changed B | Mohan’s verdict and reason |', '| --- | --- | --- |',
                           f"| {cell(pair['original']['text'])} | {cell(pair['changed']['text'])} | — |", '',
                           f"Judge same facts: **{q.get('same_facts')}**. {q.get('reason', 'unjudged')}", '',
                           '| Reply | Claim | Exact quote | Material | Status | Policy/history grounding |', '| --- | --- | --- | --- | --- | --- |']
                for variant in ('original', 'changed'):
                    for claim in q.get(variant + '_claims', []):
                        review.append('| ' + ' | '.join(cell(x) for x in (variant, claim['claim'], claim['quote'], claim['material'], claim['status'], claim['grounding'])) + ' |')
            (SAMPLE / 'native_review_samudra.md').write_text('\n'.join(review) + '\n')
            logger.write('agent_v3_validation', 'native_review_selected', seed=SEED, chat_ids=[p['chat_id'] for p in pairs], review_status='pending', evidence_ids=report['quality_evidence_ids'] + report['experiment']['evidence_ids'])
        logger.write('agent_v3_validation', 'summary_generated', ok=True, reports=[f'agent_{c}_v3_report.json' for c in results])
    print('Wrote checked completion report and native review sheet.')


if __name__ == '__main__':
    main()
