# PROMPT-06: Merge, score against the contract, README and submission files

Model: Astra
Effort: high
Why: integration across branches, a full live demo run, and long-form documentation checked against evidence.

Start after PROMPT-05B (done: `feat/ui` at `1fa98f8`) and PROMPT-04C (done: `feat/agent` at `e53c375`).

## Read first
AGENTS.md, docs/CONTRACT.md with all addenda, docs/DECLARATIONS.md, docs/METERLESS.md, docs/REPORT_SCHEMA.md, web/BILLING_SCHEMA.md, logs/sample/agent_v3_completion_report.md, logs/sample/ui_5b_completion_report.md, docs/review/2026-10-24/REVIEW.md, docs/design/reference/architecture.html.

## Step 0: merge into main (Mohan approves this by sending the prompt)
In the main checkout: `git switch main`, `git merge --ff-only feat/agent` (or a normal merge if main moved), then `git merge --no-ff feat/ui`. Resolve conflicts (expect `src/polytoken/api.py`: keep 04C's CORS and events and 05B's routes and static mount). Commit any untracked `docs/prompts/*.md` and `docs/design/reference/`. Run the full suite and `-m live`, record counts, push `main` (never force). Remove the `.cache/worktrees/*` worktrees. Then `git switch -c feat/ship main`.

## Step 0b: UI fixes found in review of the 05B screenshots
1. The screenshots use a v2 report (A/A "not measured", A/B 1/20, stamp FAILED). Re-shoot on the v3 report: A/A 7/20 and A/B 3/20 dot strips side by side, the 18-of-20 line, stamp INCONCLUSIVE and the interpretation line "the bar cannot be met by this judge and stand-in model".
2. Headline 89.2% (share of money) sits next to 96.3% (share of billed tokens) without saying which is which. Label each: "of the money" and "of billed tokens", and say once that answers cost more per token.
3. Language tax "820.65% above English" reads as noise; show "9.2x what the same content costs in English" with the money figure.
4. Duplicate stamps ("UNTESTED ESTIMATE UNTESTED ESTIMATE"): one stamp per status.
5. Resend staircase: two giant blocks with empty space. Draw each reply as one horizontal stacked bar (system prompt, history, new user turn), bars stacked downward, a cumulative-billed line beside them, compact height; label the resent system prompt once ("same 10,456 tokens, paid again").
6. Token strip: byte-level tokens show mojibake labels. Show each byte token as a hatched cell with its hex byte (for example E0 B0), and group the bytes of one Telugu character under that character.
7. Default currency INR for the demo companies (both are Indian); keep the switch.
Re-run the UI tests and refresh `logs/sample/ui_*.png`.

## Step 1: score against the pre-registered contract (`polytoken score`)
A separate offline command; the agent never imports it. For each company's latest complete run, compare the report with the contract table and write `logs/sample/contract_score.md` and `.jsonl`:
- Questions 1 to 4 answered with evidence? (yes / partly / no, with the claim ids)
- Expected top finding reached by the agent's own investigation? (pass / fail)
- Expected top fix: recommended, inconclusive or rejected, with the quality numbers (A/A floor, A/B, native review status) and the interpretation line.
- Limits respected: Nemotron, hosted and SQL counts; reasoning-loop time; job time.
- Also report, as a diagnostic, how many A/A reply pairs were byte-identical at temperature 0 and how many A/A "different" verdicts came only from added claims, so a reader can see whether the floor reflects model variation or judge strictness.
Do not change any result to fit the contract; failures and inconclusive results are reported as they are.

## Step 2: one clean demo run for the video
With `polytoken serve`, run Samudra through the UI end to end. Save the event log and report as `logs/sample/demo_samudra.jsonl` and `_report.json`, and capture screenshots of each screen to `docs/images/`.

## Step 3: README.md (rewrite for judges; every number links to its evidence file)
1. One-paragraph problem, with the experiment 01 numbers (Telugu 7.59x Llama 3.2, 1.58x Gemma 3; 18 sentences).
2. Who it is for and what it answers (the five questions).
3. What happened on the two demo companies: top finding, rupees per month before and after the measured prompt fix (₹11,015 to ₹2,230 for Samudra at 100,000 chats), quality result with the A/A floor and why the agent did not recommend the fix, speed result. Say plainly that the companies and chats are fictional and the reviews pending unless Mohan's native review is in.
4. How it works: architecture figure (export the architecture page's system diagram to `docs/images/architecture.svg` or a screenshot), the nine-step investigation, the checker.
5. Sponsor technology, one section each with file paths: Zetaris (federated SQL over company DB, measurements, reference and the REST price source, and the registration workaround), Meterless (World Model, H-MEM, Markovian, 29 ported conformance checks, signed savings), NVIDIA (Nemotron planner and judge, hosted models for experiments and speed, the probe results). Cursor was not used in this project; say so in one line.
6. Honest limits: stand-in models, synthetic data, template-ish answers, pending native review, small absolute money on a 3B model with the per-price rescale.
7. Run it: prerequisites, `.env` keys (names only), the Zetaris stack, `polytoken serve`, tests.
8. Pre-existing work declared (link docs/DECLARATIONS.md) and the independent review folder.

## Step 4: submission files
- `metadata.json` at the repo root: project name PolyToken, track "02 The Agent That Can Explain Why", team (Mohan Chelluru, solo), sponsor technologies with how each is used (Zetaris named explicitly), repository URL `https://github.com/cosmiq369/polytoken`, licence, demo video URL as an empty string for Mohan to fill.
- `docs/SUBMISSION.md`: the written explanation of how Zetaris, Meterless, NVIDIA and Cursor were (or were not) used, 300 to 500 words, plus a 150-word project summary.
- `LICENSE` (MIT) if missing.

## Step 5: release checks (do not make the repo public; that is Mohan's step)
- Secret scan of the whole history for every key name in `.env.example` and for `nvapi-`; list any hit and stop.
- No file over 5 MB committed; `.cache/`, `.venv/`, `logs/` outside `logs/sample/` ignored.
- A fresh clone in a temp folder installs with `uv pip install '.[dev]'` and passes the offline suite.

## Stop point and report
The merge result on main, commits on `feat/ship` (pushed), test counts, the contract score table, demo run summary, the secret-scan result, and every deviation. Do not merge to main.
