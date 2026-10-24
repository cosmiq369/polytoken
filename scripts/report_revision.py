"""Generate the review report only after recomputing archived measurement evidence."""
from collections import defaultdict
from pathlib import Path
import hashlib
import re

from polytoken.company_db import ROOT, jsonl, load_demo
from polytoken.logs import JsonlLogger
from polytoken.measurement_report import billed_shares, bootstrap_ratios, check_federation

SAMPLE = ROOT / 'logs/sample'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    evidence = {}
    for version,directory in [('v1',SAMPLE/'v1_recomputed'),('v2',SAMPLE)]:
        snapshots = jsonl(directory/'measurement_snapshot.jsonl')
        inputs = [i for s in snapshots for i in s['inputs']]
        counts = [c for s in snapshots for c in s['counts']]
        ratios = bootstrap_ratios(inputs,counts)
        shares = billed_shares(inputs,counts)
        assert len(ratios)==48 and len(shares)==16 and len(counts)==7168
        federation_dir = SAMPLE/'v1' if version=='v1' else SAMPLE
        check_federation(jsonl(federation_dir/'federation.jsonl')[-1]['rows'],ratios)
        evidence[version] = dict(ratios=ratios,shares=shares)
    configs,chats = load_demo()
    stats=[]
    for config in configs:
        company=config['company']
        rows=chats[company]
        sentences=[s.strip() for s in re.split(r'[.!?।]+',config['system_prompt_native']) if s.strip()]
        stats.append(dict(company=company,chats=len({r['chat_id'] for r in rows}),turns=len(rows),
                          distinct_users=len({r['text_native'] for r in rows if r['role']=='user'}),
                          distinct_answers=len({r['text_native'] for r in rows if r['role']=='assistant'}),
                          prompt_words=len(config['system_prompt_native'].split()),sentences=len(sentences),
                          distinct_sentences=len(set(sentences)),review_status='pending'))
    logger=JsonlLogger(SAMPLE)
    logger.write('data_stats','verified_v2_fixture_stats',rows=stats,seed=20261024,ok=True,
                 source='checked-in demo JSONL',query='distinct texts grouped by company/role; sentence splitting on .!?।',
                 files=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((ROOT/'data/demo').glob('*.jsonl'))])
    lines=['# PROMPT-03A verification report — 24 Oct 2026',
           'Branch: `feat/p02-fixes`, based on verified `origin/feat/data = f27d8fb`.',
           'All measurements below are recomputed from archived Zetaris rows and matched against the federation output before rendering. All reviews are pending; no price, cost or reply-time result is claimed.',
           '## Data v2',table(['Company','Chats','Turns','Distinct user turns','Distinct answers','Prompt words','Sentences / distinct'],
                              [[r['company'],r['chats'],r['turns'],r['distinct_users'],r['distinct_answers'],r['prompt_words'],f"{r['sentences']} / {r['distinct_sentences']}"] for r in stats]),
           'No assistant answer repeats within a chat. Both companies retain the 3–6 turn schedule. Fixed seed: 20261024. V1 data and original samples remain byte-for-byte archived; archive_manifest.jsonl verifies their hashes.',
           '## Vendored hashes',
           '`data/reference/seed_v0_corrected.jsonl`: `bc4166f22c9839462e0231aa919ad4287026bdc127d32d4f2eabd7b4a86e0292` (CC BY 4.0).',
           '`configs/tokenizers.yaml`: `1678b1de0327de50adc481a7c3ba384be06dfb05a2d1ceefbace383620b08424` (MIT).',
           'Harness pinned to `cosmiq369/indic-inference-tax@0f61ec90ae49082d0fef7a21774e746fe17ed1cf`; five stored counts reproduced from the installed Git dependency in a fresh non-editable venv.',
           '## V2 native-to-English ratios (ratio of sums)',
           'Columns are system prompt, user turns, assistant answers. Ratios are content-token comparisons, not money.']
    for company in ('samudra','swara'):
        groups=defaultdict(dict)
        for row in evidence['v2']['ratios']:
            if row['company']==company: groups[row['tokenizer_spec']][row['part']]=row['native_to_english_ratio']
        lines += [f'### {company}',table(['Tokenizer','System','User','Assistant'],[[s,*[f'{v[p]:.6f}' for p in ('system_prompt','user','assistant')]] for s,v in sorted(groups.items())])]
    lines += ['## Selected 95% chat-bootstrap intervals',
              '2,000 whole-chat resamples, seed 20261024, paired native/English counts, linear percentile endpoints. The same configuration in every chat gives a degenerate system-prompt interval.',
              table(['Company','Tokenizer','Part','Ratio','95% interval'],
                    [[r['company'],r['tokenizer_spec'],r['part'],f"{r['native_to_english_ratio']:.6f}",f"[{r['ci_low']:.6f}, {r['ci_high']:.6f}]"] for r in evidence['v2']['ratios'] if (r['company'],r['tokenizer_spec']) in [('samudra','unsloth/Llama-3.2-3B-Instruct'),('swara','Qwen/Qwen3-4B')]])]
    for company in ('samudra','swara'):
        lines += [f'## {company}: native token shares under both conventions',
                  'All entries are percentages. S = system share of input; O = output share of total. Billed counts replay history per completed reply; corpus counts system once per chat and every turn once.']
        by_version={v:{r['tokenizer_spec']:r for r in e['shares'] if r['company']==company} for v,e in evidence.items()}
        rows=[]
        for spec in sorted(by_version['v1']):
            row=[spec]
            for version in ('v1','v2'):
                for convention in ('corpus','billed'):
                    r=by_version[version][spec][convention]
                    row.extend([f"{100*r['system_share_of_input']:.4f}",f"{100*r['output_share_of_total']:.4f}"])
            rows.append(row)
        lines += [table(['Tokenizer','v1 corpus S','v1 corpus O','v1 billed S','v1 billed O','v2 corpus S','v2 corpus O','v2 billed S','v2 billed O'],rows)]
    lines += ['Full integer totals, English counterparts, all v1/v2 bootstrap intervals and source queries are in planted_properties.jsonl, bootstrap.jsonl and measurement_snapshot.jsonl (v1 recomputations in v1_recomputed/). Original v1 federation and shares remain in v1/.',
              '## Validation',
              "- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`: 99 passed, 6 skipped.",
              "- `uv venv .cache/pin-check` then `UV_CACHE_DIR=\"$PWD/.cache/uv\" uv pip install --python .cache/pin-check/bin/python '.[dev]'`: installed pinned Git harness in a fresh venv; no editable sibling import.",
              '- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .cache/pin-check/bin/python scripts/check_pin.py`: 99 passed, 6 skipped; all five stored counts matched. Pin provenance and exact results: pin_check.jsonl.',
              '- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" .cache/pin-check/bin/python -m pytest -q -m live`: 6 passed, 99 deselected.',
              '- `PYTHONDONTWRITEBYTECODE=1 .cache/pin-check/bin/python scripts/seed_company_db.py`: 50 chats / 223 turns per company, 118 reference variants, 0 prices; live test repeats seeding twice.',
              '- `PYTHONDONTWRITEBYTECODE=1 .cache/pin-check/bin/python scripts/register_zetaris_sources.py`: existing SQL sources refreshed and counts verified.',
              '- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .cache/pin-check/bin/polytoken measure --company all`: 16 completed batches, 7,168 rows, 48 verified federation groups; none skipped or failed.',
              '## Deviations and interpretation limits',
              '- Existing v1 samples remain unchanged in v1/. Newly computed v1 billed shares and intervals are in v1_recomputed/ so preserving the old results does not overwrite them.',
              '- Unanswered trailing user turns are excluded from billed requests. Counts exclude chat-template overhead and retries; published cache pricing is required before a discount is applied.',
              '- The fixed-seed conversations still share topic templates. Cluster intervals describe these synthetic fixtures, not a representative population or translation quality.',
              '- Tokenizer files were reused from the existing Hugging Face cache. The harness itself was fetched and installed from its public pinned Git commit, with no local editable dependency.',
              '- The requested work_state tools were not exposed in this session. Progress and evidence were retained in logs/. Network-denied sandbox attempts were retried with approved access.',
              '- Session B files, the agent loop, UI, prices, main, tags, and the sibling/platform repositories were not changed. A model setting cannot be changed by this chat; the prompt’s model/effort header was treated as execution guidance.',
              'Changed files and commit hashes are recorded in validation.jsonl and the final completion message.']
    (SAMPLE/'revision_report.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    print('Report verified and written:',SAMPLE/'revision_report.md')
    print(stats)


if __name__=='__main__': main()
