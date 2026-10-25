# PROMPT-04C completion report — 25 October 2026

Contextual A/A and A/B experiments on the declared fictional companies. The contract threshold remains 18/20; native review remains pending. Every previous run and score is retained.

## Company outcomes

| Company | A/A same facts | A/B same facts | Excluded chats (truncated) | Contract verdict | Monthly INR before → after | Speed |
| --- | --- | --- | --- | --- | --- | --- |
| samudra | 7/20 judged (target 20) | 3/20 judged (target 20) | 0 (0) | failed | 11,015.34 → 2,229.74 | inconclusive; cached timing evidence retains original time windows |
| swara | 3/20 judged (target 20) | 1/20 judged (target 20) | 0 (0) | failed | 2,386.55 → 2,447.46 | changed faster |

### Samudra

- Run: `90571737-0cb7-4f20-91fd-e11bd19c62cd`; status: complete; partial reason: none.
- Lever: `english_system`; top fix: none.
- Interpretation: **the bar cannot be met by this judge and stand-in model; result inconclusive**
- Top finding: The largest billed cost component at the quoted provider price is system_prompt.
- Model: {'changed': 'openai/gpt-oss-20b', 'control': 'openai/gpt-oss-20b', 'original': 'openai/gpt-oss-20b'}; tested on a stand-in model.
- Throughput: unavailable; missing or inseparable reasoning usage.
- Reused validated judgments: A/A 20, A/B 19. Exact model, comparison, full policy/history/replies and judge format must match; accepted judgments are not resampled.
- [Checked report](agent_samudra_v3_report.json) · [Events](agent_samudra_v3.jsonl)

| Comparison | Missing material claims | Contradicted material claims | Added material claims |
| --- | ---: | ---: | ---: |
| A/A | 1 | 1 | 19 |
| A/B | 0 | 2 | 22 |

Counts are inventory entries across both reply lists; a contradiction listed in both inventories counts twice. They are classifications by the model, not human factuality judgments.

| Timing metric | Original median [min, max] s | Changed median [min, max] s | Paired difference median [min, max] s |
| --- | --- | --- | --- |
| ttft_s | 6.62 [0.69, 32.05] | 1.19 [0.67, 1.57] | -5.06 [-31.23, -0.02] |
| latency_s | 9.34 [2.76, 33.59] | 2.41 [1.31, 2.67] | -6.72 [-32.28, -0.51] |

Latest investigation physical attempts: reasoning 12; judge 2; hosted 0; SQL 4. Job time 10.38 s.

Across all 4 retained samudra investigations: reasoning 53, judge 96, hosted 74, SQL 16 physical attempts. Limits apply per investigation; recovery totals are not hidden behind the latest run's cache hits.

### Swara

- Run: `25aa2681-6207-4782-b1ab-8b557008bf78`; status: complete; partial reason: none.
- Lever: `answer_cap`; top fix: none.
- Interpretation: **the bar cannot be met by this judge and stand-in model; result inconclusive**
- Top finding: The largest billed cost component at the quoted provider price is output.
- Model: {'changed': 'openai/gpt-oss-20b', 'control': 'openai/gpt-oss-20b', 'original': 'openai/gpt-oss-20b'}; tested on a stand-in model.
- Throughput: unavailable; missing or inseparable reasoning usage.
- Reused validated judgments: A/A 19, A/B 6. Exact model, comparison, full policy/history/replies and judge format must match; accepted judgments are not resampled.
- [Checked report](agent_swara_v3_report.json) · [Events](agent_swara_v3.jsonl)

| Comparison | Missing material claims | Contradicted material claims | Added material claims |
| --- | ---: | ---: | ---: |
| A/A | 0 | 6 | 85 |
| A/B | 2 | 7 | 29 |

Counts are inventory entries across both reply lists; a contradiction listed in both inventories counts twice. They are classifications by the model, not human factuality judgments.

| Timing metric | Original median [min, max] s | Changed median [min, max] s | Paired difference median [min, max] s |
| --- | --- | --- | --- |
| ttft_s | 0.81 [0.65, 1.09] | 0.99 [0.73, 1.07] | 0.10 [-0.12, 0.37] |
| latency_s | 13.24 [12.56, 20.03] | 2.09 [1.76, 2.87] | -11.15 [-17.16, -10.80] |

Latest investigation physical attempts: reasoning 16; judge 24; hosted 8; SQL 4. Job time 297.71 s.

Across all 2 retained swara investigations: reasoning 30, judge 69, hosted 71, SQL 8 physical attempts. Limits apply per investigation; recovery totals are not hidden behind the latest run's cache hits.

## Prior scores and run history

V2 remains Samudra **1/20** and Swara **0/20**, with the original failed-quality verdicts and diagnosis unchanged. These used the earlier protocol and are not a controlled trend comparison with v3. See [v2 report](agent_v2_completion_report.md) and [quality diagnosis](agent_v2_quality_diagnosis.md).

| Company / retained v3 attempt | Status | A/A | A/B | Reasoning / judge / hosted / SQL attempts |
| --- | --- | --- | --- | --- |
| [samudra / 622dce2a-f365-4dac-bc98-bcb5b9b85724](agent_samudra_v3_622dce2a-f365-4dac-bc98-bcb5b9b85724_report.json) | partial; insufficient sample | 0/0 | 0/0 | 14 / 45 / 66 / 4 |
| [samudra / a37e1576-89ec-4f18-897a-8fc9171101cd](agent_samudra_v3_a37e1576-89ec-4f18-897a-8fc9171101cd_report.json) | partial; insufficient sample | 7/20 | 3/17 | 13 / 45 / 0 / 4 |
| [samudra / 951bc9dc-c21d-424f-aebd-696df0ebdcd7](agent_samudra_v3_951bc9dc-c21d-424f-aebd-696df0ebdcd7_report.json) | complete; insufficient sample | 7/20 | 3/19 | 14 / 4 / 8 / 4 |
| [samudra / 90571737-0cb7-4f20-91fd-e11bd19c62cd](agent_samudra_v3_report.json) | complete | 7/20 | 3/20 | 12 / 2 / 0 / 4 |
| [swara / 374e58c5-6192-4980-96e2-c3bf6acf33ee](agent_swara_v3_374e58c5-6192-4980-96e2-c3bf6acf33ee_report.json) | partial; insufficient sample | 3/19 | 1/6 | 14 / 45 / 63 / 4 |
| [swara / 25aa2681-6207-4782-b1ab-8b557008bf78](agent_swara_v3_report.json) | complete | 3/20 | 1/20 | 16 / 24 / 8 / 4 |

## Validation

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q` — 195 passed, 8 skipped in 10.09s
- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q -m live` — 8 passed, 195 deselected in 12.65s
- `c91c997` — Register contextual quality protocol with independent A/A controls
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_agent_report.py --evidence logs/sample/agent_v2_world_events.jsonl logs/sample/agent_*v2*report.json` — 965 claims verified across three retained v2 reports; 0 drops
- `8b04c39` — Bind quality evidence to generated replies and prepare native review reports
- `1f8529e` — Use source excerpt IDs to avoid invented native-script judge quotations
- `981a9f1` — Reuse validated contextual judgments when recovering partial samples
- `76e0590` — Give bounded judge repairs exact source-reference validation feedback
- `70ba975` — Explain invalid judge fields and report all recovery attempts
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_agent_report.py --evidence logs/sample/agent_v3_world_events.jsonl logs/sample/agent_*v3*report.json` — 2,060 claims verified across all six retained v3 investigations; zero drops

## Interpretation, deviations and limitations

- Full history and policy now reach the generator/judge; GPT-OSS uses low reasoning effort and a 1024-token generation allowance. Completed answers require finish_reason=stop. One regeneration is allowed for length truncation. Selection is a fixed permutation, with exclusions before any judgments.
- A1 is shared across A/A and A/B, while A2 is independently generated. Separate replicate cache keys prevent copying the baseline into its control. Successful calls can be reused only under the same contextual protocol and settings.
- When a partial run exhausts its judge allowance, a bounded recovery reuses the first valid judgment for an exact model/comparison/full-prompt match and requests only missing verdicts. Cached raw calls remain evidence parents; all attempts and partial scores stay in history.
- Forty judgments require the pre-run addendum: 25 reasoning attempts plus 45 judge attempts. Hosted attempts remain capped at 70, SQL at 60, reasoning at six minutes and background work at thirty minutes per investigation. Any recovery runs are separately retained in the history table.
- Monthly amounts reconstruct the same historical whole-chat content bill, replacing measured system tokens only. Generated reply-length differences do not substitute for historical answers in the bill. These are quoted scenarios, not invoice totals.
- The first Samudra v3 judge format failed on malformed JSON and invented Telugu quotations. That attempt remains in history. A dated serialization addendum introduced numbered source excerpts: the judge cites IDs in English JSON, and code attaches the exact native text. Generation settings, selection and the quality bar are unchanged.
- Exact quote/schema validation and deterministic recomputation catch invented excerpts and arithmetic errors; they cannot establish whether every semantic classification is correct. Native review is pending and blocks final acceptance.
- The initial sandbox live checks could not access services. After escalation, one federation test lacked its reference-price HTTP service; starting that service resolved it. Automatic review initially rejected live generation as private-data export; exact comparison of all policy/chat fields against the fictional fixtures established synthetic provenance before retrying.
- The claude-mem work_state tools are absent from this session. Validation and protocol evidence are recorded in JSONL. The prompt header did not change the chat model/effort. No subagents were used.
- Prior samples remain unchanged. UI files and the static-file mount belong to PROMPT-05; this task adds only localhost CORS to the API.

## Mohan: native review requested

Please review the 10 fixed-seed Telugu pairs in [native_review_samudra.md](native_review_samudra.md), comparing the policy/history, both replies and judge claim inventories. Fill in same meaning / different meaning / unsure and a reason. Any different-meaning verdict blocks the fix. A Hindi reviewer must separately review ten Hindi pairs; this run does not claim that review occurred.

Evidence: [World Model closure](agent_v3_world_events.jsonl), `agent_v3_audit_*.jsonl`, and [validation](agent_v3_validation.jsonl). Stopped at PROMPT-04C.
