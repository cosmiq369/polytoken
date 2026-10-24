# PROMPT-04B completion report — 24 October 2026

The company runs used Zetaris and the one injected NVIDIA generator. Hosted work ran after the checked reasoning report, with its own deadline. All earlier PROMPT-04 samples remain unchanged. Native review is still pending.

## Commits and checks

Implementation commits on `feat/agent`:

- `a049515` Register background job limits and probe actual hosted serving
- `f0ebebc` Run bounded cached experiments after reasoning and recheck reports
- `58d23cc` Verify hosted serving and use probed GPT-OSS reasoning settings
- `8a5ed87` Exclude inseparable reasoning throughput and preserve versioned evidence archives
- `5db7ff3` Reverify completed reasoning-model reports without repeating calls
- `5662c3a` Keep sample version prefixes when archiving recovery reports

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q` — **182 passed; 8 skipped**, 6.39 s.
- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q -m live` — **8 passed; 182 deselected**, 13.68 s.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_agent_report.py --evidence logs/sample/agent_v2_world_events.jsonl logs/sample/agent_*v2*report.json` — **965 claims verified; 0 additional drops** across 3 retained runs.

Validation results are recorded in [agent_v2_validation.jsonl](agent_v2_validation.jsonl).

## Serving probe

Each row represents three short trials and three trials with Samudra’s full Telugu system prompt and one chat. TTFT is the median of successful visible-answer trials; failed or empty answers are never filled in. Every 404 was also tried without a system-role message.

| Model | Usable | Short successes / TTFT (s) | Full Telugu successes / TTFT (s) |
| --- | --- | --- | --- |
| google/gemma-3-12b-it | no | 0/3; unavailable | 0/3; unavailable |
| google/gemma-3-4b-it | no | 0/3; unavailable | 0/3; unavailable |
| meta/llama-3.2-11b-vision-instruct | no | 0/3; unavailable | 0/3; unavailable |
| meta/llama-3.2-90b-vision-instruct | no | 0/3; unavailable | 0/3; unavailable |
| openai/gpt-oss-20b | yes | 3/3; 43.78 | 2/3; 12.34 |

Both Llama endpoints timed out in the completed matrix. Both Gemma endpoints returned 404, including all retries without a system role. GPT-OSS is the only admitted family and uses the separately probed `reasoning_effort=low` setting. A cross-family model switch was therefore unavailable. Both companies used a disclosed GPT-OSS stand-in; their deployed tokenizers and quoted prices still determine the cost scenarios.

The completed GPT-OSS default-effort matrix had 3/3 short successes (median TTFT 42.96 s) and 0/3 long successes. The table above shows the follow-up low-effort matrix. All observations, including failures, are retained in [hosted_probe.jsonl](hosted_probe.jsonl), with content-addressed evidence in [hosted_probe_world_events.jsonl](hosted_probe_world_events.jsonl).

## Company outcomes

| Company | Status | Reasoning (s) | Job (s) | Nemotron / hosted / SQL attempts | Complete pairs | Same facts / judged | Dropped claims | Signed Markovian tokens / percent |
| --- | --- | ---: | ---: | --- | --- | --- | ---: | --- |
| samudra | complete | 26.86 | 1,048.56 | 16 / 58 / 4 | 20/20 | 1/20 | 9 | +50,358 / +69.88% |
| swara | complete | 16.37 | 245.91 | 17 / 4 / 4 | 20/20 | 0/20 | 0 | +62,119 / +73.55% |

Call counts are physical attempts, including retries, across reasoning and jobs. Job duration includes generation, judging and speed trials. Markovian savings are signed reference history-replay counterfactuals for the reasoning chunks, not a second measured execution; deferred judge and hosted usage are separately audited.

### Retained Swara attempt before cache recovery

- `ccf3d803-bb47-46d3-ad59-f0c34b2a9b66`: reasoning 11.05 s; job 1,798.09 s; Nemotron/hosted/SQL 9/66/4; 19/20 complete pairs; insufficient sample; stop reason wall time budget spent; 0 dropped claims; signed Markovian +12,479 tokens (+50.06%).

Across the retained Swara attempts, physical Nemotron/hosted/SQL totals are 26/70/8. The final-run table counts only newly dispatched attempts; reused evidence is not counted as a new call.

### Samudra

- Run: `ec57418c-2024-44f4-b092-686629999043`.
- Agent top finding, verbatim: **The largest billed cost component at the quoted provider price is system_prompt.**
- Agent top fix: **none**. Tested lever: `english_system`.
- Whole-chat quoted content-cost scenario: **INR 11,015.34/month before → INR 2,229.74/month after**.
- Quality verdict: **failed**; 1 same-facts passes among 20 judged pairs. Eighteen of twenty are required; native review remains pending.
- Generated output length: 5,388 → 4,921 measured tokens across twenty pairs; ratio 0.9133. This is reported separately from the historical bill.
- Speed verdict: **inconclusive**. Throughput: unavailable; inseparable reasoning usage.
- Partial reason: none.
- [Checked report](agent_samudra_v2_report.json) · [Events](agent_samudra_v2.jsonl)

### Swara

- Run: `a4f601fc-3769-48bc-9606-b7150def9364`.
- Agent top finding, verbatim: **The largest billed cost component at the quoted provider price is output.**
- Agent top fix: **none**. Tested lever: `answer_cap`.
- Whole-chat quoted content-cost scenario: **INR 2,386.55/month before → INR 2,447.46/month after**.
- Quality verdict: **failed**; 0 same-facts passes among 20 judged pairs. Eighteen of twenty are required; native review remains pending.
- Generated output length: 25,932 → 3,121 measured tokens across twenty pairs; ratio 0.1204. This is reported separately from the historical bill.
- Speed verdict: **inconclusive; cached timing evidence retains original time windows**. Throughput: unavailable; missing or inseparable reasoning usage.
- Partial reason: none.
- [Checked report](agent_swara_v2_report.json) · [Events](agent_swara_v2.jsonl)

The after amounts are deterministic scenarios, not promised savings. For prompt levers, the historical completed requests, historical replies and replay remain fixed; only measured changed-system tokens are substituted, including added instructions. Generated reply-length differences are not inserted into this bill. A quality failure prevents an accepted fix regardless of the scenario saving.

## Speed medians and spread

Values are median [minimum, maximum], seconds; four trials per variant, ABBA twice. Spread and paired differences govern the verdict, not a favorable median alone.

| Company / metric | Original | Changed | Paired difference median [min, max] |
| --- | --- | --- | --- |
| samudra / ttft_s | 25.88 [5.04, 52.29] | 27.34 [5.85, 79.43] | 2.28 [-10.82, 37.13] |
| samudra / latency_s | 27.30 [6.49, 54.42] | 28.56 [7.24, 80.28] | 2.09 [-12.01, 36.94] |
| swara / ttft_s | 25.53 [1.80, 41.22] | 21.32 [2.70, 65.84] | -0.18 [-36.20, 53.68] |
| swara / latency_s | 36.50 [12.24, 52.10] | 22.19 [3.63, 67.12] | -7.95 [-48.47, 42.16] |

## Deviations and limitations

1. Two initial probe launches were interrupted after result serialization errors. Their completed raw call/error logs and partial observations are retained; interrupted in-flight outcomes are unknown. The complete matrix was rerun after testing the recorder. No observations from those incomplete launches determined model eligibility.
2. Llama 11B answered in the aborted diagnostics but timed out on all six trials of the completed matrix. It was excluded rather than assumed available from earlier success. Gemma remained 404 with and without system roles.
3. GPT-OSS default effort produced no usable full-Telugu answer in the completed matrix, so a documented low-effort follow-up was run without raising the 200-token cap. [NVIDIA documents this option](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b-infer). Original and follow-up measurements are both retained.
4. Only GPT-OSS passed the completed serving probes, so neither run could test an actual cross-family model switch. Stand-in results do not establish deployed-model quality or latency.
5. Jobs are queued by the reasoning loop and executed by the API/CLI worker after publishing the initial checked report. The four-worker generation pool is separate from the six-minute reasoning allowance. Speed trials preserve the sequential ABBA protocol. CLI waits for completion; restart recovery requires a rerun, which reuses successful evidence.
6. Samudra was already running when unseparated reasoning usage was identified. Its completed report was reverified offline from the same evidence, dropping nine unsupported throughput claims without network calls. The original report remains in `agent_samudra_v2_report_before_throughput_correction.json`. Swara uses the corrected throughput logic directly. TTFT and total latency are retained.
7. Swara’s first planner stopped reasoning early after queuing its job; the early-stop reason remains in the initial running-report audit. One changed reply exhausted its retries, leaving 19 pairs and an insufficient-sample verdict with no judge calls. The first job reached its thirty-minute boundary (with the two-second finalization reserve), retaining six valid speed trials. One bounded recovery investigation was requested for the same answer_cap lever, reusing 39 successful generation calls and six speed trials while retrying the one missing reply and two missing speed trials. The initial attempt is retained; this was not a contract or threshold change.
8. Native spot checks have not been performed. Automated quality failure and insufficient sample remain distinct. Cost projections exclude chat-template overhead, retries and unpublished cache discounts.
9. The requested claude-mem work-state tools were unavailable, and memory capture initially reported a quota cooldown. The worker was not restarted. The chat’s model/effort settings were not changed by the prompt header; no subagents were used.
10. Sandbox escalation was required for local service access, NVIDIA calls, and Git metadata/push. Automatic approval review initially rejected the push because the destination and company-data provenance were unverified. Read-only GitHub checks confirmed the authenticated owner’s private repository and ADMIN permission; all three snapshot texts exactly matched the declared fictional fixtures, and the secret scan passed. These checks are recorded before retrying the upload. No secrets were committed. The contract received only the required dated pre-run addendum; it was not adjusted during either company rerun.

## Evidence archive

- `agent_samudra_v2.jsonl`, `agent_swara_v2.jsonl` and their checked reports.
- `agent_v2_world_events.jsonl`: complete transitive evidence closure for replay.
- `agent_v2_audit_*.jsonl`: all model attempts, errors, SQL, planner decisions, native review, Markovian, cache and checker records for these runs.
- `hosted_probe*.jsonl`: every retained serving diagnostic and archived probe evidence.
- `agent_v2_validation.jsonl`: exact validation commands, results, evidence checks and the throughput correction.

Stopped at the PROMPT-04B checkpoint; no UI, native review, contract scoring, tags or release was started.
