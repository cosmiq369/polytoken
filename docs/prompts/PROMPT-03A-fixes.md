# PROMPT-03A: Version lock, self-contained repo, billed-token accounting, demo data v2

Model: Astra
Effort: high
Why: a long, tool-heavy session (fresh venv, Docker, re-seeding, re-measuring 8 tokenizers, Zetaris verification) where staying on task matters more than peak focus on one file.

Runs in parallel with PROMPT-03B (Meterless engines) in a separate working copy. File ownership is split below; never edit a file the other session owns.

## Read first
- AGENTS.md, docs/CONTRACT.md, docs/DECISIONS.md, docs/DECLARATIONS.md
- docs/prompts/PROMPT-02-fixes-and-data.md and your PROMPT-02 report
- src/polytoken/company_db.py, measure.py, measurement_report.py, scripts/generate_demo_data.py

## Branch
`git fetch origin`, confirm `origin/feat/data` is `f27d8fb`, then `git switch -c feat/p02-fixes f27d8fb`. Small commits. Push the branch only. Do not touch `main`, no merge, no tags.

## Independent review of PROMPT-02 (what the reviewer found)
Verified: all 48 native/English ratios and all 16 planted shares reproduced exactly by separate code (raw Hugging Face tokenizers, no polytoken or indictax code); 86 passed / 6 skipped reproduced on a clean Linux copy at f27d8fb; the limiter held at most 38 starts in any rolling 60 s window over 400 saturated calls; no secret from .env appears in any tracked file or in history. Good work. Findings to fix here:

- **F3 (accounting).** Your decision note was right that the corpus convention is not billed tokens. Chat APIs keep no state, so reply k re-sends the system prompt and every earlier turn. Reviewer's numbers at f27d8fb: Swara's output share is 78.5% of tokens on Llama 3.2 under the corpus convention but 46.8% of billed tokens; Samudra's system prompt is 98.2% of billed input on Llama 3.2. Cost must use billed tokens.
- **F4 (pseudo-replication).** Each company has 99 assistant turns but only 20 distinct answers (61 and 56 distinct user turns), and 12 chats per company repeat the same answer twice. Any interval over 99 "pairs" is too narrow.
- **F5 (padded prompt).** Samudra's Telugu system prompt closes all 20 paragraphs with the same three sentences (124 sentences, 67 distinct). It reads as padding to anyone who opens the data.
- **F6 (hidden local dependency).** Runtime code reads `../solve-it/data/prompts/seed_v0_corrected.jsonl` and `../solve-it/configs/tokenizers.yaml`. The corrected corpus is not in the public indictax repo at all, so a judge who clones PolyToken cannot seed. A version pin alone does not fix this.

## Step 1: version lock and a self-contained repo (F6)
1. `pyproject.toml`: depend on `indictax @ git+https://github.com/cosmiq369/indic-inference-tax@0f61ec90ae49082d0fef7a21774e746fe17ed1cf`. Keep `scripts/install-indictax.sh` only as an optional editable override for local development and say so in README.md. (Reviewer checked: `indictax/tok.py` and `configs/tokenizers.yaml` at that commit are byte-identical to the working copy you used; `corpus.py` differs only in per-language review support that PolyToken does not use.)
2. Copy, read-only, `../solve-it/data/prompts/seed_v0_corrected.jsonl` to `data/reference/seed_v0_corrected.jsonl` and `../solve-it/configs/tokenizers.yaml` to `configs/tokenizers.yaml`. Write `data/reference/SOURCES.md` with each file's origin, licence (corpus CC BY 4.0) and sha256. Expected: corpus `bc4166f22c9839462e0231aa919ad4287026bdc127d32d4f2eabd7b4a86e0292`, tokenizers.yaml `1678b1de0327de50adc481a7c3ba384be06dfb05a2d1ceefbace383620b08424`. Stop and report if either differs.
3. Point every default path in `src/` and `scripts/` at the in-repo copies. Test: no file under `src/` or `scripts/` (except `install-indictax.sh`) contains the string `solve-it`.
4. Fix the harness URL in AGENTS.md and docs/DECLARATIONS.md: `github.com/mohanchelluru369-tech/indic-inference-tax` is wrong; the repo is `github.com/cosmiq369/indic-inference-tax`. In DECLARATIONS.md also list the pinned commit, the two vendored files with hashes, and this row: `Meterless engines (World Model, H-MEM, Markovian) | github.com/Meterless/Meterless at 1742dec56a66e58eef9dda2d2b865823758ca8cd, Apache-2.0 | Python implementation from the specs, conformance checks ported to pytest; see docs/METERLESS.md`.
5. Pin check: in `.cache/pin-check/` create a fresh venv with `uv venv`, `uv pip install '.[dev]'` (no local solve-it anywhere on the path), then run the offline suite and a script that recounts five stored measurement texts with the pinned install and compares them with their stored token counts. Write the result to `logs/sample/pin_check.jsonl`.

## Step 2: billed-token accounting (F3)
1. Contract addendum, appended under "Addenda" in docs/CONTRACT.md (never edit the text above it), dated 24 Oct 2026, saying: written after the PROMPT-02 measurements and before any price or cost exists; money uses billed tokens of a stateless chat API (for reply k: input = system prompt + every earlier user and assistant turn + user turn k; output = reply k); the corpus convention stays reported for transparency; cached-prefix pricing is used only where a provider publishes a cache price; the expected findings are unchanged and are judged on cost and reply time, not on token share.
2. `measurement_report.py`: add `billed_tokens(chat_rows, counts)` and `billed_shares(...)` returning, per company and tokenizer, billed input, billed output, system share of billed input, output share of billed total, and the same under the corpus convention. Record both conventions in `logs/sample/planted_properties.jsonl`.
3. Hand-computed test: chat with system 100, u1 10, a1 20, u2 5, a2 30 gives billed input (100+10) + (100+10+20+5) = 245 and billed output 50.

## Step 3: demo data v2 (F4, F5), disclosed, never hidden
Your PROMPT-02 decision note says data will not be adjusted after seeing results. These changes fix realism defects found in review, not results, so they go through a dated addendum and v1 stays in the repo with its results:
1. Move the current files to `data/demo/v1/` and the current samples to `logs/sample/v1/`, unchanged. Add a second contract addendum explaining F4 and F5 and that both versions' results are reported.
2. Regenerate `data/demo/` (v2) with a fixed seed:
   - Samudra's Telugu system prompt: still 600 to 900 whitespace words, no sentence repeated, and long for the reason real support bots are long: role and tone, safety rules, plus embedded knowledge (a fictional plan catalogue, troubleshooting steps for network, SIM, recharge, billing and roaming, escalation rules). English version alongside. Replies must stay in Telugu.
   - Per company: 50 chats of 3 to 6 turns as before, at least 80 distinct user turns and at least 45 distinct assistant answers, and no answer repeated within a chat. Samudra answers stay short and draw on the prompt's knowledge, so a quality judge has facts to check. Swara keeps a short system prompt and long spoken-style Hindi answers.
   - Every row `review_status = 'pending'`.
3. Re-seed, re-measure all eight tokenizers, re-run the federation verification, and regenerate `logs/sample/` for v2.
4. Cluster bootstrap for each per-part ratio: resample chats with replacement (the system prompt counts once per resampled chat), B = 2000, fixed seed, 95% percentile interval. Test: 10 chats with one answer each, then the same 10 chats with every answer repeated three times inside its chat; with the same seed both give the identical interval (a turn-level bootstrap would wrongly narrow the second).

## Files you own (session B owns everything under src/polytoken/meterless/, tests/meterless/, docs/METERLESS.md, src/polytoken/cli.py and logs/sample/meterless_*)
pyproject.toml, AGENTS.md, README.md, docs/CONTRACT.md (addenda only), docs/DECISIONS.md, docs/DECLARATIONS.md, data/**, configs/**, sql/**, scripts/**, src/polytoken/{company_db,measure,measurement_report,prices,config}.py, logs/sample/** except meterless_*, tests for those modules.

## Tests
- Default suite and `-m live` both green; the pin check green in the fresh venv.
- New tests: no `solve-it` paths; billed-token fixture; bootstrap repeated-turn test; v2 data checks (distinct counts, no repeated answer within a chat, no repeated sentence in Samudra's prompt, word count 600 to 900).

## Do not
- Write prices, mark reviews, or edit the contract above "Addenda".
- Touch ../solve-it or ~/zetaris-platform beyond read-only copying and inspection; no git commands in ../solve-it.
- Start the agent loop or the UI.

## Stop point and report
Stop when everything above is green and pushed. Report:
1. Commits on `feat/p02-fixes` and files changed.
2. Test commands and summaries, including the pin check.
3. Vendored file hashes.
4. v2 data stats: distinct user turns and answers per company, Samudra prompt words and distinct sentences.
5. v2 ratio table (both companies, three parts, eight tokenizers) with bootstrap intervals for Samudra on Llama 3.2 and Swara on Qwen3.
6. Shares under both conventions for v1 and v2, per tokenizer.
7. Every deviation, with the reason.
