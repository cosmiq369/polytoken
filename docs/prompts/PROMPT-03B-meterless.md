# PROMPT-03B: Meterless engines (World Model, H-MEM, Markovian) with ported conformance suites

Model: Sol
Effort: high
Why: focused coding against three explicit specs with exact numeric checks; correctness per function matters more than session length.

Runs in parallel with PROMPT-03A in a separate working copy. Never edit a file that session owns (listed at the end).

## Read first
- AGENTS.md (the Meterless lines and the logging rules), src/polytoken/llm.py (`NvidiaGenerator`), src/polytoken/logs.py (`JsonlLogger`)
- The Meterless specs at a pinned commit. Clone them into the ignored cache, read only:
  `git clone https://github.com/Meterless/Meterless.git .cache/meterless && git -C .cache/meterless checkout 1742dec56a66e58eef9dda2d2b865823758ca8cd`
  - `engines/world-model/AGENTS.md`, `engines/world-model/conformance/runner.ts`
  - `engines/markovian/AGENTS.md`, `engines/markovian/docs/efficiency-model.md`, `engines/markovian/conformance/runner.ts`
  - `engines/hmem/AGENTS.md`, `engines/hmem/conformance/runner.ts`, `engines/hmem/conformance/vectors/vectors.json`
  - The TypeScript in each `reference/src/` may be read to settle an ambiguity. Do not run npm or any of that code.

## Working copy and branch
If you are not already in a separate worktree, create one inside the repo's ignored cache:
`git fetch origin && git worktree add .cache/worktrees/meterless -b feat/meterless f27d8fb`
Work only there. Make its own venv: `uv venv`, then `uv pip install "indictax @ git+https://github.com/cosmiq369/indic-inference-tax@0f61ec90ae49082d0fef7a21774e746fe17ed1cf"` and `uv pip install -e '.[dev]'`. For live runs, pass the main checkout's `.env` by absolute path to `load_settings(env_file=...)`; never copy it. Small commits; push `feat/meterless` only. Do not touch `main`, no merge, no tags.

## What to build (Python 3.10+, standard library only, no new dependencies)
Package `src/polytoken/meterless/`, provider-agnostic: the only model access is an injected generator callable, `NvidiaGenerator` in production and fakes in tests.

### Markovian (`markovian.py`)
- `ChunkConfig` with the spec's defaults and bounds; out-of-range values raise a typed error, never clamp. Load-time check `chunkSize >= framingTokens + carryoverTokens + outputBudget`.
- Marker protocol `[STATE_CHECKPOINT]` / `[TASK_COMPLETE]`; markers drive completion and never appear in display output. Carryover bounded by `carryoverTokens`.
- `overlapTokens`: reject any non-zero value with an error that names `overlapTokens` (a conforming choice; accepting and ignoring it fails conformance).
- Every run record carries its `chunkConfig` snapshot and a `tokenLabel`: `measured` when the generator returns usage token counts (NvidiaGenerator does), else `estimated` (characters / 4).
- `model_totals(n)` and `run_efficiency(chunks, config)` exactly as `docs/efficiency-model.md` and spec section 6. A reflection failure never fails the run.
- Log projected savings (`model_totals` for the run's config) and actual savings (`run_efficiency` on the run's own tokens) to `logs/markovian.jsonl` through `JsonlLogger`.

### World Model (`world_model.py`)
- Append-only canonical event log in SQLite (path passed in; default `.cache/state/world.sqlite`; tests use tmp paths), with entities, contexts, relationships and derived views.
- Stable ids exactly as the reference: `normalize_name` = NFKD, then strip only U+0300 to U+036F, strip U+200B to U+200D and U+FEFF, lowercase, collapse whitespace, trim; `entity_id_from_name(type, name)` = `ent_` + first 16 hex of sha256(`type:normalized`).
  **Trap:** the obvious Python port, dropping every Unicode mark (category M), wrecks Indian scripts. Reviewer's check: it makes `दवा` (medicine) and `दव` one entity, `किताब` and `कताब` one entity, and `రేషన్ కార్డు` equal to the meaningless `రషన కరడ`, because vowel signs and the virama are marks. The reference strips only the Latin diacritic block. Add tests that these pairs stay distinct while `José García` and `Jose Garcia` merge.
- `decide(score)` merge bands; writes without provenance rejected; idempotent ingest (the same batch twice gives an empty diff); bitemporal edges (a superseding edge closes the old one; point-in-time queries respect validity); an audit entry per mutation, in order.
- Provenance on every observation per AGENTS.md: source, query, time window, fetched_at.
- PolyToken adapter (`evidence.py`): evidence kinds `measurement`, `query_result`, `price`, `timed_call`, `quality_verdict`, `claim`, each written as an event with provenance; `evidence_for(claim_id)` returns the supporting events. The checker in PROMPT-04 will read only from here.

### H-MEM (`hmem.py`)
- Tiers `short_term`, `working`, `long_term`; a record without a source is rejected; feedback deltas, clamps, ranking rules, conflict gate (the loser gets `supersededBy`, nothing deleted), append-only trust ledger, sleep guardrails and dream approval exactly as the spec and `vectors.json` say.
- Retrieval uses the spec's hybrid signals with a deterministic local embedder (hashed character n-grams); no model downloads.
- PolyToken adapter (`company_memory.py`): company profile memories (monthly volume, reply-time target, model in use, constraints such as "replies stay in Telugu", past findings linked to World Model evidence ids), each with source and confidence.

## Conformance, ported faithfully
`tests/meterless/test_conformance_markovian.py`, `..._world_model.py`, `..._hmem.py`: port every check in the three runners and every case in `vectors.json` at the pinned commit (8 Markovian, 8 World Model, 13 H-MEM). Keep each check's id in the test name (`test_eff_001_...`) with the same inputs and expected numbers. All 29 must pass. If any check cannot be ported as written, list it in docs/METERLESS.md with the reason; never weaken an expected value.

## Real-data proof and production size
- `polytoken engines-demo` in `cli.py`:
  - default (offline): a 4-chunk Markovian run with a fake generator; prints projected vs actual savings; ingests the evidence rows from `logs/sample/federation.jsonl` (read only) into a temporary World Model and prints entity, event and audit counts.
  - `--live [--env-file PATH]`: at most 3 Markovian chunks through `NvidiaGenerator` (`tokenLabel` must be `measured`); writes `logs/sample/meterless_markovian_live.jsonl`.
- Production size: one investigation writes up to about 10,000 evidence rows (7,168 measurement rows exist today). Test that ingesting 7,168 rows uses batched transactions (at most 10 commits) and finishes in under 5 s on the laptop. Test that a Markovian run never calls the generator more than `maxChunks` times plus one reflection call.
- The NVIDIA rate limiter is per process. Do not run live calls while another session is running live calls.

## docs/METERLESS.md
Per engine: what was built, where it is used in PolyToken, the conformance table (check id, test name, status), what was deliberately left out (Scout Intent; any H-MEM behaviour beyond the conformance surface that PolyToken does not use), and the Apache-2.0 attribution for the specs and ported checks.

## Files you own
src/polytoken/meterless/**, tests/meterless/**, docs/METERLESS.md, src/polytoken/cli.py, logs/sample/meterless_*.
Session A owns pyproject.toml, AGENTS.md, README.md, docs/CONTRACT.md, docs/DECISIONS.md, docs/DECLARATIONS.md, data/**, configs/**, sql/**, scripts/**, the other modules under src/polytoken/ and the rest of logs/sample/. If you need a change there, put it in your report instead.

## Do not
- Add dependencies, run npm, or vendor Meterless code; implement from the specs.
- Start the agent loop, the tools or the UI (PROMPT-04 and 05).

## Stop point and report
Stop when all tests are green and the branch is pushed. Report:
1. Commits on `feat/meterless` and files created.
2. Test summaries: default suite, `tests/meterless` with all 29 check ids and their status, and `-m live` if run.
3. `engines-demo` output, offline and live: projected vs actual savings, `tokenLabel`, World Model counts.
4. The Indic stable-id test results.
5. Anything in the specs you found ambiguous and how you resolved it.
6. Every deviation, with the reason.
