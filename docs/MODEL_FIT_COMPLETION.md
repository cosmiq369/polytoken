# PROMPT-08 completion — 25 October 2026

PolyToken now answers which model fits an Indian-language workload and budget. The data, agent, deterministic checker, offline replay, Companies screen and submission prose use the model-fit story. Four fresh live investigations are complete, with checked profiles, per-model rankings, source receipts and recorded service timings.

## Changes and commits

| Commit | Change |
| --- | --- |
| `dee7fab` | Registered the dated question, withdrawal and four predictions before new data. |
| `fa2f9b6` | Added four workloads, expanded prices, SQL projections and measurement coverage. |
| `1f6df0a` | Implemented checked model-specific ranking, constrained advice and offline scoring. |
| `d01d388` | Added Model fit and four-company views, evidence receipts and browser proof tooling. |

The closing evidence commit contains this report, the refreshed submission/README/deck/video text, all new replay evidence, screenshots and recording, plus a score-table layout correction. The feature branch is `feat/model-fit`; publication uses a fast-forward to `main`.

## Data and measurement coverage

Each company has 40 fictional conversations, English system instructions and `review_status=pending`. The fixed seed is `20261025`, dataset version `model-fit-v1`. Previous data is preserved under `data/demo/v2/`. All eight tokenizers completed for all four workloads; federation verified 96 company/tokenizer/part groups. Eleven dated provider quotes cover eight distinct priced models; four unpriced families remain tokenizer-fit-only.

[Data hashes and measurement runs](../logs/sample/model_fit_measurements/manifest.jsonl) · [Measurement audit](../logs/sample/model_fit_measurements/audit.jsonl) · [Federation proof](../logs/sample/model_fit_measurements/federation.jsonl) · [Price sources](../data/reference/SOURCES.md).

## Checked profiles

Script shares count user turns. Turns include both user and assistant rows. Answer share counts newly generated answer tokens as a fraction of reconstructed billed tokens using the current tokenizer; earlier answers also appear in replayed input history. English-term share is the documented lexicon heuristic, excluding numbers from its word denominator.

| Company | Channel | Native / romanized / mixed | Turns / conversation | New-answer token share | Recognized English-term share | Monthly volume | Configured target |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Samudra Telecom | chat | 10.6% / 16.0% / 73.4% | 4.7 | 20.8% | 38.6% | 200,000 | 8 s |
| Swara Care | voice | 100.0% / 0.0% / 0.0% | 4.5 | 47.6% | 0.0% | 120,000 | 3 s |
| Raitu Mitra | voice | 100.0% / 0.0% / 0.0% | 4.0 | 49.2% | 0.0% | 80,000 | 3 s |
| Paisa Saathi | chat | 0.0% / 0.0% / 100.0% | 4.0 | 15.7% | 42.1% | 300,000 | 6 s |

Unknown-script share is zero in these fictional samples. Chat targets are displayed as configuration; the deployment-latency gate in this task applies to voice.

## Top three, recommendation and reasons

Amounts below are USD per 1,000 completed conversations, using each model family’s measured tokenizer and that provider’s dated quote. Ratios compare the same workload with its paired English version. Costs exclude provider templates, retries, taxes and unpublished cache discounts. All model quality is **verify on your sample**.

### Samudra Telecom

Run `51c08db4-cb64-4dcb-b408-247af607c95e` · [Checked report](../logs/sample/agent_samudra_model_fit_report.json)

| Rank | Model | Provider | USD / 1,000 | Tokens / English |
| ---: | --- | --- | ---: | ---: |
| 1 | meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | $0.00928250 | 1.5421× |
| 2 | google/gemma-3-4b-it | Parasail (via OpenRouter) | $0.01219425 | 1.1952× |
| 3 | openai/gpt-oss-20b | DeepInfra (via OpenRouter) | $0.01441025 | 1.2034× |

**Conditional recommendation: meta-llama/Llama-3.1-8B-Instruct.** Most user turns are code-mixed or romanized, and new answers account for a smaller part of billing than in the voice workloads. Llama 3.1 8B has a higher token ratio than Gemma but its lower dated quote wins on this exact mixture.

**Runner-up:** google/gemma-3-4b-it at the second quote above. **Avoid on cost alone:** Qwen/Qwen3-4B — Fireworks AI (serverless size tier 4B-16B), $0.07444000 per 1,000. It has the highest quoted content cost among the distinct-model options here; this is not a quality rejection. The report retains the profile, cost and ratio claim IDs supporting each explanation.

### Swara Care

Run `8a28287f-6121-4451-b3f3-657bd62854d6` · [Checked report](../logs/sample/agent_swara_model_fit_report.json)

| Rank | Model | Provider | USD / 1,000 | Tokens / English |
| ---: | --- | --- | ---: | ---: |
| 1 | google/gemma-3-4b-it | Parasail (via OpenRouter) | $0.02412400 | 1.1124× |
| 2 | meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | $0.03148850 | 2.1887× |
| 3 | google/gemma-3-12b-it | DeepInfra (via OpenRouter) | $0.04055300 | 1.1124× |

**Cost candidate only: google/gemma-3-4b-it.** Devanagari user turns and long spoken answers make tokenizer coverage and output pricing consequential. Gemma 3 4B has the lowest reconstructed bill. Exact-model/provider/workload latency is missing, so the agent withholds a voice-qualified recommendation.

**Runner-up:** meta-llama/Llama-3.1-8B-Instruct at the second quote above. **Avoid on cost alone:** Qwen/Qwen3-4B — Fireworks AI (serverless size tier 4B-16B), $0.36644000 per 1,000. It has the highest quoted content cost among the distinct-model options here; this is not a quality rejection. The report retains the profile, cost and ratio claim IDs supporting each explanation.

### Raitu Mitra

Run `54fedfdb-8f96-49d4-94ad-6f1ef07a1e5f` · [Checked report](../logs/sample/agent_raitu_model_fit_report.json)

| Rank | Model | Provider | USD / 1,000 | Tokens / English |
| ---: | --- | --- | ---: | ---: |
| 1 | google/gemma-3-4b-it | Parasail (via OpenRouter) | $0.01832875 | 1.3543× |
| 2 | google/gemma-3-12b-it | DeepInfra (via OpenRouter) | $0.02889000 | 1.3543× |
| 3 | openai/gpt-oss-20b | DeepInfra (via OpenRouter) | $0.03103250 | 1.4175× |

**Cost candidate only: google/gemma-3-4b-it.** Telugu-script user turns and medium rural-advisory answers favor the Gemma quote and tokenizer on this workload. The runner-up uses the same tokenizer with a different model price; this says nothing about equal quality. Missing voice latency prevents a deployment recommendation.

**Runner-up:** google/gemma-3-12b-it at the second quote above. **Avoid on cost alone:** meta-llama/Llama-3.3-70B-Instruct — DeepInfra (via OpenRouter), $0.33382000 per 1,000. It has the highest quoted content cost among the distinct-model options here; this is not a quality rejection. The report retains the profile, cost and ratio claim IDs supporting each explanation.

### Paisa Saathi

Run `c87da357-0457-4ba0-8cbb-e1189af8dbff` · [Checked report](../logs/sample/agent_paisa_model_fit_report.json)

| Rank | Model | Provider | USD / 1,000 | Tokens / English |
| ---: | --- | --- | ---: | ---: |
| 1 | meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | $0.00541150 | 1.0885× |
| 2 | google/gemma-3-4b-it | Parasail (via OpenRouter) | $0.00930175 | 1.0444× |
| 3 | openai/gpt-oss-20b | DeepInfra (via OpenRouter) | $0.01060350 | 1.0611× |

**Conditional recommendation: meta-llama/Llama-3.1-8B-Instruct.** Short Hinglish conversations contain many recognized English product terms. Llama and Gemma token ratios are close on this mixture; the lower Llama 3.1 8B quote gives the cheapest reconstructed bill.

**Runner-up:** google/gemma-3-4b-it at the second quote above. **Avoid on cost alone:** Qwen/Qwen3-4B — Fireworks AI (serverless size tier 4B-16B), $0.04779000 per 1,000. It has the highest quoted content cost among the distinct-model options here; this is not a quality rejection. The report retains the profile, cost and ratio claim IDs supporting each explanation.

## Addendum score and run budgets

All four profile predictions, four cost-candidate predictions and four constraint-handling checks pass: **12 of 12 checks**. Voice abstention is the required outcome when matching timing is unavailable. These results validate the fictional demonstration and do not establish model quality.

[Readable score](../logs/sample/model_fit_score.md) · [Exact score, claim IDs and evidence references](../logs/sample/model_fit_score.jsonl).

| Company | Checked claims | Nemotron calls | SQL queries | Reasoning seconds | Hosted / judge calls |
| --- | ---: | ---: | ---: | ---: | --- |
| Samudra Telecom | 361 | 13 | 4 | 24.118 | 0 / 0 |
| Swara Care | 363 | 13 | 4 | 27.862 | 0 / 0 |
| Raitu Mitra | 365 | 11 | 4 | 21.889 | 0 / 0 |
| Paisa Saathi | 367 | 12 | 4 | 14.632 | 0 / 0 |

All recorded budgets were respected. No numeric claims were dropped in the four completed reports. The first partial Samudra run remains archived; the scorer selects the latest complete run by authenticated evidence time. No new candidate-serving or quality result is implied by these investigation timings.

## Validation

| Exact command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 235 passed, 8 live tests skipped in 166.07 s (final implementation, including the score-table layout correction). |
| `.venv/bin/python -m pytest -q -m live` | 8 passed, 234 deselected in 18.86 s. Run before one additional non-live classifier case was added. |
| `node web/check-model-fit.cjs` | Passed real offline API validation; 20 dark/light desktop/mobile screenshots and replay recording. |
| `node web/check-console.cjs` | Passed replay, scrubber, nested timings, navigation, contrast, mobile, keyboard, zoom and reduced-motion checks. |
| `node web/check-ui.cjs` | Passed all 17 saved reports; also exercised through the full pytest suite. |
| `.venv/bin/polytoken score` | Four companies pass; claims and recommendations recomputed from authenticated evidence. |
| `.venv/bin/python scripts/ship_secret_scan.py` | No configured-secret or provider-credential hits in reachable Git history or tracked/untracked non-ignored files. |
| `git diff --check` | Passed. |

Chromium required execution outside the sandbox. An obsolete headline expectation found during the suite was corrected. Final command results are recorded in [model-fit validation](../logs/sample/model_fit_validation.jsonl); [console proof](../logs/sample/console_validation.jsonl) and [secret scan](../logs/sample/ship_secret_scan.jsonl) retain their prior records.

## Screenshots and replay

28 screenshots cover Companies and every company in desktop/mobile dark/light views, plus desktop ranking details. The browser check asserts eight priced models and four unpriced families per company, checked cost values, voice abstention, receipts, fresh timings, text contrast, 320 px reflow, keyboard navigation, no external requests and no page errors.

| Screen | Dark | Light |
| --- | --- | --- |
| Companies desktop | [Open](images/model_fit_companies_desktop_dark.png) | [Open](images/model_fit_companies_desktop_light.png) |
| Companies mobile | [Open](images/model_fit_companies_mobile_dark.png) | [Open](images/model_fit_companies_mobile_light.png) |
| Samudra Telecom desktop | [Open](images/model_fit_samudra_desktop_dark.png) | [Open](images/model_fit_samudra_desktop_light.png) |
| Samudra Telecom mobile | [Open](images/model_fit_samudra_mobile_dark.png) | [Open](images/model_fit_samudra_mobile_light.png) |
| Samudra Telecom ranking | [Open](images/model_fit_samudra_ranking_dark.png) | [Open](images/model_fit_samudra_ranking_light.png) |
| Swara Care desktop | [Open](images/model_fit_swara_desktop_dark.png) | [Open](images/model_fit_swara_desktop_light.png) |
| Swara Care mobile | [Open](images/model_fit_swara_mobile_dark.png) | [Open](images/model_fit_swara_mobile_light.png) |
| Swara Care ranking | [Open](images/model_fit_swara_ranking_dark.png) | [Open](images/model_fit_swara_ranking_light.png) |
| Raitu Mitra desktop | [Open](images/model_fit_raitu_desktop_dark.png) | [Open](images/model_fit_raitu_desktop_light.png) |
| Raitu Mitra mobile | [Open](images/model_fit_raitu_mobile_dark.png) | [Open](images/model_fit_raitu_mobile_light.png) |
| Raitu Mitra ranking | [Open](images/model_fit_raitu_ranking_dark.png) | [Open](images/model_fit_raitu_ranking_light.png) |
| Paisa Saathi desktop | [Open](images/model_fit_paisa_desktop_dark.png) | [Open](images/model_fit_paisa_desktop_light.png) |
| Paisa Saathi mobile | [Open](images/model_fit_paisa_mobile_dark.png) | [Open](images/model_fit_paisa_mobile_light.png) |
| Paisa Saathi ranking | [Open](images/model_fit_paisa_ranking_dark.png) | [Open](images/model_fit_paisa_ranking_light.png) |

[Replay recording](images/model_fit_replay.webm) · [Three-minute narration script](VIDEO_SCRIPT.md) · [Updated deck text](DECK_TEXT.md).

## Evidence and limits

[Compressed World Model closure](../logs/sample/model_fit_v1_world_events.jsonl.gz) contains all five runs, including the partial run. The accompanying `model_fit_v1_audit_*.jsonl` files preserve agent, planner, checker, model-fit, H-MEM, Markovian, Nemotron and Zetaris activity. Earlier reviews, datasets and audit records remain historical evidence.

The data is fictional, template-based and pending native review. Script and English-term classifiers are transparent heuristics. Shared tokenizer families do not establish equal quality or latency. Only GPT-OSS passed the recorded serving probe; the optional A/A-controlled answer-length protocol remains available, but its stand-in results cannot validate the ranked candidates. Exact-model/provider/workload voice latency is unverified. The public submission video URL remains empty pending an upload.

The local saved demo is served with `.venv/bin/polytoken serve --demo` at [127.0.0.1:8000](http://127.0.0.1:8000). It replays recorded evidence without provider calls.
