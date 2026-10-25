# PROMPT-05: The PolyToken interface: a billing console for multilingual AI

Model: Sol
Effort: high
Why: focused front-end work against a fixed schema, with a small API addition.

Runs in parallel with PROMPT-04C. You own `web/**`, `data/reference/fx.json` and its loader, and new routes you add to `src/polytoken/api.py` in their own functions (change nothing else there). PROMPT-04C adds CORS and may add events; build against docs/REPORT_SCHEMA.md and ignore unknown fields.

## Working copy
`git fetch origin && git worktree add .cache/worktrees/ui -b feat/ui origin/feat/agent`, work only there. Push `feat/ui` only. Commit `docs/design/reference/` from the main checkout into this branch as reference material.

## Read first
- docs/REPORT_SCHEMA.md and the saved reports `logs/sample/agent_*_report.json` (your fixtures)
- `docs/design/reference/*.html`: an earlier draft, in a canvas format that does not render on its own. Use it only as a list of what each screen contains. Do not copy its layout or look.

## Who it is for and what they decide
The user is the engineering or product lead who owns an Indian-language AI product and its bill. In under a minute they must answer:
1. What do we pay, per month, per conversation and per reply?
2. How much of that is the language tax: what we pay above the same content in English?
3. Where does it come from: system prompt resent every reply, replayed history, user turns or answers?
4. Which fix saves the most, is it safe for quality, and what does it do to reply time?
5. What happens if volume, price or the model changes?
Every screen element must serve one of these five. Anything that serves none is cut.

## Design language: "The Token Ledger"
An auditor's ledger, not a generic SaaS dashboard: calm paper surfaces, every figure in a monospaced numeral font with aligned digits, verdicts as stamps (VERIFIED, INCONCLUSIVE, FAILED, NOT TESTABLE, STAND-IN), and every number one click from its receipt. Commit to this and make it distinctive:
- Colour carries meaning, and only two accents: turmeric (#B7791F, text-safe #8A5A12) = the language tax and cost; deep indigo (#2E3A8C) = verified evidence and good outcomes. Ink #16181D, paper #FAF8F3, lines #E3DED3; a true dark mode (ink-blue ground, paper-tinted text) that keeps the same meanings.
- Type: a system serif or grotesque for headings, system sans for text, `ui-monospace` with tabular numerals for all figures. Telugu and Devanagari render correctly everywhere (fallback to Noto Sans Telugu and Devanagari); the product's tagline appears in English, Telugu and Hindi.
- No gradients, glows, emoji, decorative illustrations or left-border cards. Hand-drawn SVG for every chart; no chart library.
- Plain HTML, CSS and JavaScript in `web/`, no framework, no CDN, no npm. Works at 390 px wide; real `<button>`, `<label>`, `<input>`; text contrast at least 4.5:1; keyboard reachable.

## Currency
- Report money stays in USD (the canonical unit). Change `data/reference/fx.json` to `{"base": "USD", "rates": [{"currency": "INR", "per_usd": 94.9432, "source": "...", "source_url": "...", "as_of": "...", "fetched_at": "...", "verified": true}]}`, keeping today's INR values exactly, plus the loader and its tests. Adding a currency later = one more row with a source.
- `GET /currencies` returns USD plus every verified rate. The header has a currency switch (USD, INR, any future row); the choice is remembered per browser. The rate's source and date show wherever converted money appears.

## The screens
1. **Ask.** Company picker (from `GET /companies`, showing language, model in use and monthly volume), editable question, optional volume and reply-time target, Investigate.
2. **Live investigation, as a case file.** Each step is a case entry with a stamp (measured, located, hypothesised, tested, judged, timed, checked), the tool, the planner's one-sentence why, and the finding. Background experiment progress (done, failed, total). Budget gauges in the margin: Nemotron calls, hosted calls, SQL queries, time. Evidence cards arrive alongside, each opening its receipt.
3. **Billing report.** In this order:
   - **Headline strip:** monthly cost; cost per 1,000 conversations; cost per reply; **language tax** = cost above the same content in English, as money and %; the tax multiplier for the company's model (for example ×9.49, with English drawn as ×1.0).
   - **Where the bill comes from:** a stacked bar of billed tokens per conversation (system prompt resent, replayed history, user turns, answers), Billed / Transcript toggle, plus the **resend factor** (how many times the system prompt is paid per conversation) and the **cacheable share** (input that is an identical prefix every reply).
   - **Resend staircase:** one median conversation drawn as steps, each reply's input = prompt + history, showing why cost grows faster than the transcript.
   - **Fix ladder:** a waterfall from today's monthly cost through each fix to the after-fix cost, ranked by saving. Each fix shows saving in money and %, a quality verdict as two 20-dot strips (A/A floor and A/B) against the 18-of-20 line, reply-time change, and its stamp. Rejected or untestable fixes stay visible with the reason.
   - **Model comparison:** cost per conversation for each model with a verified price, with that tokenizer's multiplier and lone-byte share; models without a verified price are listed as "no verified price", never estimated.
   - **What-if panel:** monthly volume and input/output price sliders that rescale cost and savings in the browser, clearly labelled "what-if, not measured", resettable to measured values.
   - **Trust line:** claims checked and claims dropped (with reasons on click), signed Markovian savings for the run (a loss shown below zero), and native review status.
4. **Why Telugu costs more (token strip).** The same sentence, one row per tokenizer, cut at its token boundaries; lone-byte or partial-character tokens hatched; tokens per word and lone-byte share at the end of each row. Add `GET /tokens?text=...&tokenizer=...` returning token pieces through `polytoken.tokens` (local tokenizer files only; refuse unknown tokenizers). Default sentences come from the company's own chats via the report's evidence, editable by the user.
5. **Receipt view.** For any figure: the claim, the formula with its inputs, provenance (source, query, fetched_at, run id), the raw rows or call record, and the checker's stamp.

Every number comes from the report, events or the API. The only browser calculations are currency conversion with the shown rate and the labelled what-if panel. Missing values show "not measured" with the report's reason.

## Tests
- `tests/test_ui_static.py`: `/` serves the page; every field the page reads exists in REPORT_SCHEMA or the new endpoints; every saved report fixture loads without error (headless browser if Playwright is available on the Mac).
- fx loader: list format, INR value unchanged, unverified rows refused; `/currencies`; `/tokens` refuses unknown tokenizers and returns pieces whose join equals the input.

## Stop point and report
Commits; screenshots of every screen with the saved Samudra report, in light and dark and at 390 px (`logs/sample/ui_*.png`); test results; any metric you could not show and why; deviations.
