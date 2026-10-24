# PROMPT-04 completion report — 24 October 2026

Implementation is on `feat/agent`. Both companies were investigated through Zetaris and NVIDIA. No quality-validated fix was established: hosted timeouts and unavailable endpoints prevented complete A/B evidence. All runs, including the original failed/partial attempt, are retained. No UI or contract scoring was performed.

## Validation

- Prerequisite: main contained `893eb28` and `1eecb62`; 135 passed, 6 skipped before changes.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`: **169 passed, 8 skipped** (final rerun: 2.85 s).
- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q -m live`: **8 passed, 169 deselected** (13.81 s).
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_agent_report.py logs/sample/agent_*report.json`: **875 claims replayed, zero drops**, from curated World Model evidence alone.
- `polytoken serve --port 8014`: live companies, persisted CLI UUID report, evidence, OpenAPI and registered price URL all passed. The temporary verification server was shut down.
- Scripted full run at 50 chats: 13 Nemotron, 48 hosted and 4 SQL calls. Hidden-file isolation, second-run memory recall, every budget boundary, planner repair/fallback, tamper rejection, exact/ratio/money tolerances, throughput recomputation, failed calls, stand-in labels and SSE replay/order are covered.

## Every live investigation

Counts below are BudgetGuard counts for the agent. Startup REST readiness checks and catalogue discovery are logged separately. The first two reports include about 0.07 s of finalization after the six-minute external-work cutoff; final code reserves two seconds for report finalization.

| Run | Status | Duration (s) | Nemotron / hosted / SQL | Complete A/B pairs | Quality judged / passed | Valid speed runs | Signed Markovian tokens / percent |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| [Samudra initial](agent_samudra_64196e67-85ca-4606-978c-2cccc5618654_report.json) | partial | 360.069 | 10 / 40 / 4 | 6/20 | not reached | 0/8 | +14,768 / +51.15% |
| [Samudra corrected](agent_samudra_report.json) | partial | 360.064 | 9 / 47 / 4 | 0/20 | 0/20 judged; 0 pass | 3/8 | +9,831 / +46.33% |
| [Swara](agent_swara_report.json) | complete | 342.310 | 14 / 50 / 4 | 0/20 | 0/20 judged; 0 pass | 1/8 | +44,501 / +68.73% |

Signed Markovian values are the reference history-replay counterfactual, not a measured second execution or total investigation bill. Hosted experiments are excluded from its chunk token accounting. Unknown usage from a failed Nemotron call makes the initial run an estimate; the later Swara report labels that historical run accordingly. Original reports/logs are unchanged.

### Samudra

- Run: `2720ac99-fd83-4531-ae4a-adb42e275cd4`.
- Agent finding, verbatim: **The largest billed cost component at the quoted provider price is system_prompt.**
- Agent top fix: **none**. The tested model-switch candidate was rejected because quality could not be established.
- Baseline whole-chat content-cost scenario: **INR 11,015.34/month** at the configured volume and quoted Parasail (via OpenRouter) price. **After-fix monthly cost: unavailable**; incomplete A/B pairs do not support it.
- Quality: **0 of 20 judged**, 0 positive verdicts. This is incomplete judging, not twenty measured semantic failures. All native reviews remain pending.
- Speed: **3 of 8 valid runs**. Medians, paired difference and spread are unavailable because complete four-per-variant evidence is missing.
- Claims dropped: **0**. Missing A/B money and speed aggregates were never proposed as claims; the tamper test independently proves dependent claims are dropped.
- Partial reason: wall time budget spent.
- Hosted model disclosure: tested on a hosted model in the same tokenizer family; not the deployed model.
- Compared hosted models: `meta/llama-3.2-11b-vision-instruct` → `openai/gpt-oss-20b`.
- Ranked hypotheses (unvalidated savings, not accepted recommendations):

  - `model_switch` (openai/gpt-oss-20b): INR 9,645.90/month expected saving; rejected. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.
  - `model_switch` (unsloth/gemma-3-4b-it): INR 9,414.39/month expected saving; untested estimate. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.
  - `english_system`: INR 8,792.18/month expected saving; untested estimate. Measured system-language substitution; reply-language instruction overhead and generated answers require experiment.
  - `answer_cap`: INR 516.82/month expected saving; untested estimate. Hypothesis assumes half as many answer tokens, including replay; no measured cap benefit yet.
  - `model_switch` (Qwen/Qwen3-4B): INR -23,982.35/month expected saving; untested estimate. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.

### Swara

- Run: `66f0a95a-adf4-4540-b4c7-12f5a03cef2d`.
- Agent finding, verbatim: **The largest billed cost component at the quoted provider price is output.**
- Agent top fix: **none**. The tested model-switch candidate was rejected because quality could not be established.
- Baseline whole-chat content-cost scenario: **INR 2,386.55/month** at the configured volume and quoted Fireworks AI (serverless size tier 4B-16B) price. **After-fix monthly cost: unavailable**; incomplete A/B pairs do not support it.
- Quality: **0 of 20 judged**, 0 positive verdicts. This is incomplete judging, not twenty measured semantic failures. All native reviews remain pending.
- Speed: **1 of 8 valid runs**. Medians, paired difference and spread are unavailable because complete four-per-variant evidence is missing.
- Claims dropped: **0**. Missing A/B money and speed aggregates were never proposed as claims; the tamper test independently proves dependent claims are dropped.
- Partial reason: none; workflow completed with rejected/unavailable experimental results.
- Hosted model disclosure: tested on a stand-in model.
- Compared hosted models: `meta/llama-3.2-11b-vision-instruct` → `google/gemma-3-4b-it`.
- Ranked hypotheses (unvalidated savings, not accepted recommendations):

  - `model_switch` (unsloth/gemma-3-4b-it): INR 2,251.45/month expected saving; rejected. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.
  - `model_switch` (openai/gpt-oss-20b): INR 2,114.77/month expected saving; untested estimate. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.
  - `model_switch` (unsloth/Llama-3.2-3B-Instruct): INR 1,254.59/month expected saving; untested estimate. Quoted alternate tokenizer/provider scenario; hosting and output quality remain untested.
  - `answer_cap`: INR 833.86/month expected saving; untested estimate. Hypothesis assumes half as many answer tokens, including replay; no measured cap benefit yet.
  - `english_system`: INR 336.12/month expected saving; untested estimate. Measured system-language substitution; reply-language instruction overhead and generated answers require experiment.

## Historical F7 audit: every original Meterless live run

| Original run | Signed tokens | Signed percent |
| --- | ---: | ---: |
| `47019b37-9a22-4509-a6b2-8ab700fc8e9e` | -1,359 | -65.27% |
| `13b81b33-c18d-41a2-b924-1c16ef671d6d` | +735 | +32.84% |
| `896cd3a3-f9d7-426f-a86e-97aadffe2379` | +735 | +32.84% |

The original negative run is explicitly retained. Source: `meterless_markovian_live.jsonl`; derived audit: `meterless_signed_audit.jsonl`.

## Limitations and deviations

1. Samudra was run twice because its initial planner exhausted the small output allowance without valid JSON. Direct-answer mode fixed most planner failures; both attempts remain in the logs and reports. Provider failures continued, so neither run validates a fix.
2. The NVIDIA catalogue advertised the selected endpoints, but hosted Llama calls repeatedly timed out. An isolated post-run, minimal temperature-zero Gemma probe returned HTTP 404. That single hosted diagnostic is separate from the three investigation budgets and is retained in `agent_hosted_diagnostics.jsonl` and the World Model archive.
3. Same-family hosted Llama is not the deployed Llama 3B model. Swara uses an explicitly labelled stand-in because Qwen 3 is absent. All experimental token/money projections use the company tokenizer and quoted price. A model-switch price scenario and its generated-output experiment remain distinct.
4. One full A/B experiment is scheduled per investigation, with other hypotheses retained as untested estimates. The seventy-call cap cannot fit two forty-call A/B experiments plus speed probes. Provider retries count against that cap.
5. A/B money uses one sampled last-turn response per chat; the historical baseline reconstructs all completed replies and replayed history. They are not interchangeable. No after-fix money is shown for these incomplete samples.
6. The stale REST price schema required `DROP LIGHTNING DATABASE TABLE polytoken_reference.prices` and recreation at the identical URL. A normal Spark REFRESH and DROP did not repair it. Only application-owned metadata changed; all staged reference values remain byte-identical.
7. Short deployed model names from Zetaris are resolved to a unique measured tokenizer by exact name/suffix, rather than guessed hardcoded mappings.
8. Native review remains pending. A rejected incomplete experiment is not a demonstrated quality failure. All sixty sampled pairs are retained in the native-review audit, including missing-answer failures.
9. Earlier deadline reports finalized about seventy milliseconds after the external-work cutoff. The final guard reserves two seconds for checking and serialization. Report durations and original events were not rewritten.
10. The initial Markovian report labelled usage measured despite one failed Nemotron attempt with unknown usage. Historical loading now marks that run estimated; its original signed figure and label are preserved for audit. Later reports and this summary disclose the limitation.
11. Final hardening rejects placeholder planner explanations, requires a billed-saving ranking explanation, links remembered findings to baseline evidence, distinguishes budget-blocked requests from physical attempts, exposes redacted HTTP error details, and fixes persisted CLI UUID lookup. The retained live reports predate some of this hardening; final code is covered by the full suite, not presented as another unperformed live investigation.
12. Startup catalogue discovery and REST readiness/metadata checks are outside the agent tool budgets and logged separately. No investigation tool reads docs, demo fixtures, scripts or sample logs. Evidence replay/curation scripts are explicitly offline post-run utilities.
13. Live federation validation originally appended to existing curated samples and broke a fixed-size conformance fixture. The new rows were preserved separately as `p04_*`; the original sample files were restored byte-for-byte, and live tests now write to `logs/live_validation/`.
14. The requested claude-mem work_state tools were unavailable. Execution evidence is in JSONL logs. The chat cannot switch its own model/effort, so the prompt header was treated as execution guidance; no subagents were used.
15. Local services, dependency installation and git metadata/push needed approved sandbox escalation. No secrets, sibling-repository changes, main merges, tags, releases, UI work or contract scoring are included.

16. Automatic push review initially held the upload for destination/payload verification. The configured origin was verified as the private `cosmiq369/polytoken` repository with ADMIN access, and every archived source text was matched exactly to the declared fictional demo fixtures; the full secret scan passed.

## Implementation commits

- `fade191` — Record review evidence, verified references and signed Markovian savings
- `7bf863f` — Implement bounded planner, sourced tools and deterministic report checker
- `96d5959` — Expose investigation API, replayable events and one-command demo service
- `4f70677` — Use direct structured Nemotron replies and bound concurrent experiments
- `a29397f` — Harden report provenance, deadline finalization and persisted API reads
- `4d14acf` — Recompute throughput from raw usage and retain diagnostic evidence

`6b478cb` archived all three live outcomes and replay evidence. A final audit commit records destination verification.

The following evidence-only commit contains this report and the complete curated run artifacts; its hash is reported in the completion message.

## Created files

- `data/reference/fx.json`
- `data/reference/nvidia_hosted.json`
- `docs/REPORT_SCHEMA.md`
- `docs/review/2026-10-24/REVIEW.md`
- `docs/review/2026-10-24/fx.json`
- `docs/review/2026-10-24/nvidia_hosted.json`
- `docs/review/2026-10-24/prices.json`
- `docs/review/2026-10-24/recompute_p02.py`
- `docs/review/2026-10-24/recompute_v2.py`
- `docs/review/2026-10-24/v2_extra.py`
- `logs/sample/agent_audit_agent.jsonl`
- `logs/sample/agent_audit_agent_markovian.jsonl`
- `logs/sample/agent_audit_checker.jsonl`
- `logs/sample/agent_audit_hmem.jsonl`
- `logs/sample/agent_audit_llm_calls.jsonl`
- `logs/sample/agent_audit_native_review.jsonl`
- `logs/sample/agent_audit_planner.jsonl`
- `logs/sample/agent_audit_zetaris_queries.jsonl`
- `logs/sample/agent_completion_report.md`
- `logs/sample/agent_hosted_diagnostics.jsonl`
- `logs/sample/agent_llm_errors.jsonl`
- `logs/sample/agent_replay.jsonl`
- `logs/sample/agent_samudra.jsonl`
- `logs/sample/agent_samudra_64196e67-85ca-4606-978c-2cccc5618654_report.json`
- `logs/sample/agent_samudra_report.json`
- `logs/sample/agent_swara.jsonl`
- `logs/sample/agent_swara_report.json`
- `logs/sample/agent_validation.jsonl`
- `logs/sample/agent_world_events.jsonl`
- `logs/sample/meterless_signed_audit.jsonl`
- `logs/sample/p04_bootstrap.jsonl`
- `logs/sample/p04_federation.jsonl`
- `logs/sample/p04_planted_properties.jsonl`
- `scripts/check_agent_report.py`
- `scripts/curate_agent_samples.py`
- `src/polytoken/agent/__init__.py`
- `src/polytoken/agent/budget.py`
- `src/polytoken/agent/calculations.py`
- `src/polytoken/agent/planner.py`
- `src/polytoken/agent/runner.py`
- `src/polytoken/agent/runtime.py`
- `src/polytoken/api.py`
- `src/polytoken/checker.py`
- `src/polytoken/reference.py`
- `src/polytoken/reference_server.py`
- `src/polytoken/tools/__init__.py`
- `tests/test_agent.py`
- `tests/test_agent_live.py`

Main interfaces: `src/polytoken/tools/`, `src/polytoken/agent/`, `src/polytoken/checker.py`, `src/polytoken/api.py`, `docs/REPORT_SCHEMA.md`. The replayable World Model archive contains 180 events including the diagnostic; the three reports reference 179 investigation events.
