# PROMPT-04: The investigating agent: planner, tools, checker, budgets, live event stream

Model: Astra
Effort: high
Why: the longest build of the project, mixing code with live runs against Zetaris and the NVIDIA API; staying on task across many tool calls matters most.

## Read first
- AGENTS.md, docs/CONTRACT.md including both addenda, docs/DECISIONS.md, docs/METERLESS.md
- logs/sample/revision_report.md (PROMPT-03A results) and docs/review/2026-10-24/REVIEW.md (reviewer findings F7, F8 and the staged reference data)
- src/polytoken/{llm,zetaris,measurement_report,prices}.py and src/polytoken/meterless/

## Branch
Mohan merges both PROMPT-03 branches into `main` before this prompt. Confirm `main` contains `893eb28` and `1eecb62` and that the suite gives 135 passed, 6 skipped; if not, stop and report. Then `git switch -c feat/agent main`. Small commits, push the branch only. No merge to main, no tags.

## Step 0: reference data and review fixes
1. Copy `docs/review/2026-10-24/prices.json` over `data/reference/prices.json` (it must pass `load_prices` unchanged). Add `data/reference/fx.json` and `data/reference/nvidia_hosted.json` from the same folder, with small fail-closed loaders (refuse `verified: false`). Commit the whole `docs/review/2026-10-24/` folder as review evidence.
2. **F7 (signed savings).** Keep the spec's clamped `tokensSaved` for conformance, and also log `net_tokens = standardCost - markovianCost` (signed) and `net_percent`. Anything shown to a person uses the signed values. A report that quotes a run lists every run in that log, not only the best.
3. **F8 (completion).** Never rely on the model typing `[TASK_COMPLETE]`. The planner returns validated JSON; your wrapper around the planner writes the Markovian markers itself (`[STATE_CHECKPOINT]` with the carryover, or `[TASK_COMPLETE]` when the planner says done or a budget is spent).
4. Contract addendum, dated 24 Oct 2026, written before any investigation run, appended under the existing addenda: the 25-call limit covers the agent's own Nemotron calls (planner and judge); calls to hosted models that run a fix experiment or a speed probe have a separate cap of 70 per investigation; all of them go through the one shared rate limiter. A fix is tested A/B on the same hosted model with the same user turns at temperature 0, original system prompt against changed one, so the model is not a confounder.

## Step 1: tools (`src/polytoken/tools/`)
Every tool writes what it observed to the World Model through `EvidenceStore`, with source, query, time window and fetched_at, and returns the evidence ids. No tool reads files under `docs/`, `data/demo/`, `scripts/` or `logs/`: company data comes only through Zetaris SQL, reference data through the loaders above.
- `sql(query)`: Zetaris, SELECT only, schemas `company_systems` and `polytoken_reference` only; counts toward the 60-query budget.
- `token_meter(company, part, variant)`: reads measurement rows through Zetaris; measures new text (a changed system prompt, generated answers) with `polytoken.tokens` and records it as new evidence.
- `billed_cost(company, tokenizer, variant, price_entry)`: billed tokens per chat with `measurement_report.billed_tokens`, then money with `prices.cost_usd` and `fx.json` at the company's `monthly_chats` from `bot_config`. When no verified price exists, it returns "money unavailable" and the report says so. Also return the saving per Rs 1 of input price per million tokens, so a reader on a different model can rescale it.
- `fix_experiment(company, lever, hosted_model)`: for 20 chats chosen by fixed seed, generate the reply to each chat's last user turn twice on the same hosted model (original and changed system prompt, temperature 0), through the shared limiter. Levers: English system prompt with replies kept in the company's language; answer-length cap; model switch (compare the original prompt on the current family's hosted model with the same prompt on another family's hosted model). Hosted models only from `nvidia_hosted.json`, intersected at startup with a live `/v1/models` call. When the company's own family has no hosted model (Swara's Qwen 3), run the A/B on a stand-in hosted model and label every result from it "tested on a stand-in model"; token and money figures still use the company's real tokenizer. Never present a stand-in result as the company's model.
- `quality_judge(pairs)`: Nemotron, 5 pairs per call, returns per pair `same_facts: true|false` with a one-line reason. Pass needs at least 18 of 20. Queue every pair for native review (`review_status = pending`) and show that in the report.
- `speed_probe(hosted_model, variants)`: time to first token and output tokens per second, ABBA order, 4 runs per variant, streamed, from response usage. Report medians, the paired difference and "inconclusive" when the run-to-run spread covers the difference.

## Step 2: the agent (`src/polytoken/agent/`)
- The investigation is one Markovian run; each chunk is one step: clarify, measure, locate, hypothesise, experiment, judge, speed, check, report. Use `carryoverTokens = 512`; the carryover holds evidence ids and findings, not raw rows.
- Planner: Nemotron through `NvidiaGenerator`, JSON out: `{"why": "<= 40 words shown to the user", "tool": "...", "args": {...}, "done": false}`. Invalid JSON gets one repair retry, then a deterministic fallback for that step, logged as `fallback`.
- Clarify reads `bot_config` through Zetaris and the company's H-MEM profile; it asks the user only for what neither holds. It saves volume, target and constraints (for example, replies stay in Telugu) to H-MEM with sources. A second investigation of the same company must show what it remembered.
- Locate uses billed shares per part. Hypothesise ranks levers by expected billed saving and must explain why in the `why` field.
- `BudgetGuard`: 25 Nemotron calls, 70 hosted calls, 60 SQL queries, 6 minutes of wall time. Hitting any limit ends the run with a partial report marked `partial` and the reason.

## Step 3: the checker (`src/polytoken/checker.py`)
Every number in a report is a claim `{id, text, value, unit, evidence_ids, recompute}`. The checker recomputes each value from the World Model evidence alone, with exact integers, ratios within 1e-9 relative, and money to 0.01. A claim that fails or has no evidence is dropped and listed with the reason. The report is built only from claims that pass. Test: tamper one stored measurement and the claims built on it must be dropped.

## Step 4: API and events (`src/polytoken/api.py`)
FastAPI and uvicorn are allowed as new dependencies; nothing else new.
- `POST /investigations {company, question, monthly_chats?, latency_target_s?}` returns an id.
- `GET /investigations/{id}/events`: server-sent events `step_started`, `tool_called`, `evidence_added`, `finding`, `budget`, `claim_dropped`, `done`, each with a timestamp and the step's `why`.
- `GET /investigations/{id}/report`, `GET /evidence/{id}`, `GET /companies`.
- `polytoken serve` starts everything the demo needs in one command, including the price endpoint Zetaris reads (fold in `scripts/serve_reference.py` and keep the registered URL working).
- Write `docs/REPORT_SCHEMA.md`: the report JSON and every event's fields. PROMPT-05 builds the UI on it; it shows rupees per month, per-part billed shares, the ratio per tokenizer with its interval, fixes ranked by saving with quality and speed results, rejected fixes with the reason, dropped claims, and the signed Markovian savings.

## Step 5: live runs
`polytoken investigate --company samudra` and `--company swara`, live, one at a time. Save each run's full event log and report to `logs/sample/agent_samudra.jsonl`, `agent_swara.jsonl` and the matching report JSON. Do not open docs/CONTRACT.md during or between these runs to adjust anything; scoring against it is PROMPT-06.

## Tests
- Each tool with fakes; planner JSON validation, repair and fallback; BudgetGuard at every limit; the checker tamper test; SSE event order for a scripted run.
- Isolation: during a scripted investigation, any attempt to open a path under `docs/`, `data/demo/`, `scripts/` or `logs/sample/` fails the test.
- Production size: a scripted investigation at 50 chats makes at most 25 Nemotron calls, 70 hosted calls and 60 SQL queries; count them.
- Default suite and `-m live` green.

## Do not
- Edit docs/CONTRACT.md above the addenda, mark reviews, or change prices or fx values.
- Build the UI (PROMPT-05) or score against the contract (PROMPT-06).

## Stop point and report
Stop when both live runs have finished and the branch is pushed. Report:
1. Commits on `feat/agent` and files created.
2. Test summaries, default and live.
3. For each company: duration, Nemotron, hosted and SQL counts, the top finding and top fix as the agent stated them, rupees per month before and after, quality result (n of 20), speed result with spread, claims dropped and why, and signed Markovian savings.
4. Anything the agent could not do and how the report says so.
5. Every deviation, with the reason.
