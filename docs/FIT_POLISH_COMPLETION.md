# PROMPT-08B completion

Currency follows the saved, sourced display rate on Companies and Model fit. Monthly costs use each company’s authenticated configuration. Per-1,000 costs remain secondary, and all multiples use unrounded checked costs. INR rounds to whole rupees above one rupee; USD to cents above one dollar; sub-unit values keep two significant digits (at least two decimal places).

“Cheap per token” means the lower half of distinct models ordered by the price of an equal input/output token basket, with deterministic model/provider ties. Avoid selects the largest checked tokens/English ratio among those cheap models whose workload cost exceeds the best fit and whose token ratio exceeds one. The most expensive model stays in the ranking.

The headline adapts when the lowest unit quote is also the cheapest workload model, so it does not assert a false cost reversal. Quality remains pending; both voice companies still abstain from a latency-qualified deployment recommendation.

## Checked comparisons

| Company | Monthly conversations | Best content-cost fit | Cheapest per token | × best fit | Avoid tokenizer penalty |
| --- | ---: | --- | --- | ---: | --- |
| [Samudra Telecom](../logs/sample/agent_samudra_model_fit_report.json) | 200,000 | Llama-3.1-8B-Instruct: ₹176 ($1.86) | Llama-3.1-8B-Instruct: ₹176 ($1.86) | 1.00× | gpt-oss-20b |
| [Swara Care](../logs/sample/agent_swara_model_fit_report.json) | 120,000 | gemma-3-4b-it: ₹275 ($2.89) | Llama-3.1-8B-Instruct: ₹359 ($3.78) | 1.31× | Llama-3.1-8B-Instruct |
| [Raitu Mitra](../logs/sample/agent_raitu_model_fit_report.json) | 80,000 | gemma-3-4b-it: ₹139 ($1.47) | Llama-3.1-8B-Instruct: ₹363 ($3.83) | 2.61× | Llama-3.1-8B-Instruct |
| [Paisa Saathi](../logs/sample/agent_paisa_model_fit_report.json) | 300,000 | Llama-3.1-8B-Instruct: ₹154 ($1.62) | Llama-3.1-8B-Instruct: ₹154 ($1.62) | 1.00× | gpt-oss-20b |

### Samudra Telecom

The lowest unit price also wins on this measured workload: Llama-3.1-8B-Instruct quotes the lowest price but needs 1.54× English tokens on your Telugu code-mixed traffic. 1.00× the best fit’s content cost.

Checked dependencies in the [saved report](../logs/sample/agent_samudra_model_fit_report.json): `fit/b5ee979f82b14ebd/usd_per_1000`, `fit/b5ee979f82b14ebd/token_ratio`, `profile/monthly_conversations`, `profile/code_mixed_share`.

### Swara Care

Cheapest per token is not cheapest for your users: Llama-3.1-8B-Instruct quotes the lowest price but needs 2.19× English tokens on your Hindi native script traffic. 1.31× the best fit’s content cost.

Checked dependencies in the [saved report](../logs/sample/agent_swara_model_fit_report.json): `fit/cd986269fa4448c8/usd_per_1000`, `fit/b5ee979f82b14ebd/usd_per_1000`, `fit/b5ee979f82b14ebd/token_ratio`, `profile/monthly_conversations`, `profile/native_script_share`.

### Raitu Mitra

Cheapest per token is not cheapest for your users: Llama-3.1-8B-Instruct quotes the lowest price but needs 5.03× English tokens on your Telugu native script traffic. 2.61× the best fit’s content cost.

Checked dependencies in the [saved report](../logs/sample/agent_raitu_model_fit_report.json): `fit/cd986269fa4448c8/usd_per_1000`, `fit/b5ee979f82b14ebd/usd_per_1000`, `fit/b5ee979f82b14ebd/token_ratio`, `profile/monthly_conversations`, `profile/native_script_share`.

### Paisa Saathi

The lowest unit price also wins on this measured workload: Llama-3.1-8B-Instruct quotes the lowest price but needs 1.09× English tokens on your Hindi code-mixed traffic. 1.00× the best fit’s content cost.

Checked dependencies in the [saved report](../logs/sample/agent_paisa_model_fit_report.json): `fit/b5ee979f82b14ebd/usd_per_1000`, `fit/b5ee979f82b14ebd/token_ratio`, `profile/monthly_conversations`, `profile/code_mixed_share`.

Monthly USD = checked `usd_per_1000` × checked `profile/monthly_conversations` / 1,000. INR = USD × the [recorded FX rate](../data/reference/fx.json), ₹94.9432/USD as of 23 October 2026. Ratio = checked model cost / checked lowest content cost. Underlying prices and counts retain their original Zetaris evidence; report views were rebuilt without new provider measurements.

## Verification

- `.venv/bin/python -m pytest -q`: **241 passed, 8 skipped in 170.73s**; skipped tests require explicit live opt-in.
- `NODE_PATH=/Users/mohan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node web/check-model-fit.cjs`: **passed**, 28 screenshots and refreshed replay.
- `.venv/bin/python scripts/ship_secret_scan.py`: **passed**, no configured secret values or credential patterns in worktree or reachable history.
- `git diff --check`: **passed**.

The first suite attempt could not launch Chromium inside the macOS sandbox. The permitted rerun exposed a legacy assertion expecting paise; it now checks whole-rupee rounding. The final full suite above passed. The demo was stopped before the final suite and restarted with `.venv/bin/polytoken serve --demo` after validation.

Browser checks cover USD/INR on both screens, every ranked cost multiple, sub-unit rounding, four workloads, eight priced models each, voice abstention, evidence receipts, light/dark contrast, 320px reflow, keyboard navigation, no external requests and no page errors. [Browser audit](../logs/sample/model_fit_validation.jsonl) · [Comparison audit](../logs/sample/fit_polish_validation.jsonl).

## Visual proof

[Companies](images/model_fit_companies_desktop_dark.png) · [Samudra](images/model_fit_samudra_desktop_dark.png) · [Swara](images/model_fit_swara_desktop_dark.png) · [Raitu](images/model_fit_raitu_desktop_dark.png) · [Paisa](images/model_fit_paisa_desktop_dark.png) · [Raitu ranking](images/model_fit_raitu_ranking_dark.png) · [Replay recording](images/model_fit_replay.webm). All 28 `model_fit_*` screenshots were refreshed in desktop/mobile and dark/light variants.
