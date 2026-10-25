# PROMPT-05B: Turn the interface into the billing console

Model: Sol
Effort: high
Why: focused front-end work plus three small API routes, against a written spec.

## Context
`feat/ui` (`21e4050`) implemented an earlier draft of PROMPT-05. The current `docs/prompts/PROMPT-05-ui.md` (re-read it now, in full) is the spec: billing-lead questions, "The Token Ledger" design language, currency switch, headline strip, resend staircase, fix ladder, model comparison, what-if panel, token strip, receipts. Figures the report lacks (language tax, resend factor, cacheable share, staircase, model comparison) come from a new module `src/polytoken/billing_view.py` and route `GET /investigations/{id}/billing`, computed deterministically from World Model evidence and recomputed by the existing checker functions; do not edit the agent, tools or checker files PROMPT-04C is changing. Keep everything that already works (event replay, receipts, escaping, missing-data handling, tests) and close the gaps below. Same ownership rules as PROMPT-05; PROMPT-04C is still running on `feat/agent`, so do not touch its files.

## Working copy
Continue in `.cache/worktrees/ui` on `feat/ui`. Push `feat/ui` only.

## Gaps against the spec (reviewer, from `ui_report.png`)
1. **Currency switch missing.** Implement fx.json as a list, the loader, `GET /currencies`, the header switch (USD, INR, future rows) remembered per browser, with rate source and date beside converted money.
2. **Headline reads like a log line** ("...component at the quoted provider price is system_prompt."). Write it for a person: "Your Telugu system prompt is 96% of what you pay: it is sent again with every reply." Then the headline strip: monthly cost, cost per 1,000 conversations, cost per reply, language tax (money and %), and the multiplier for the company's model with English as ×1.0. If the language-tax figure is not in the report, serve it from `/billing` (cost of the same content in English, from measured English tokens), never computed in the browser.
3. **Resend factor, cacheable share and resend staircase** are missing. Add them (from `/billing`).
4. **Fixes list is not a ladder.** Draw the waterfall from today's monthly cost to the after-fix cost for fixes with a measured saving. A negative "saving" (Qwen3 switch, −₹23,982) is a cost increase: show it below the line in a separate "would cost more" group, never in a list "ranked by saving". Untested estimates are visually distinct from tested fixes.
5. **Model comparison** (cost per conversation per verified-price model, multiplier, lone-byte share) is missing. The ratio list currently repeats degenerate intervals like "9.49 – 9.49" for the system prompt; show an interval only when its width is non-zero and say why the system prompt has none (one prompt per company).
6. **What-if panel** (volume and price sliders, labelled "what-if, not measured", reset) is missing.
7. **Token strip screen** and `GET /tokens` are missing. Build it as specified, with default sentences from the company's chats.
8. **Quality** shows "A/A floor: not measured". Keep that for old reports; render PROMPT-04C's A/A and A/B dot strips with the 18-of-20 line and the interpretation line when present.
9. **Dropped claims** show raw ids (`speed/output_tokens_per_s/original_median`). Show a readable name and the reason; keep the id in the receipt.
10. **Reply time** must state the stand-in model by name next to the numbers, not only in a footnote.
11. **Design language.** The current page is a neat generic dashboard. Apply the Token Ledger: paper ground #FAF8F3, turmeric for cost and the tax, indigo for verified evidence, tabular monospaced figures, verdict stamps, trilingual tagline, true dark mode. Remove anything that serves none of the five questions.

## Tests
Extend `tests/test_ui_static.py` for the new endpoints, currency switching, negative-saving placement, non-zero interval rule and readable dropped-claim names. Keep the 390 px, light, dark and contrast checks.

## Stop point and report
Commits, tests, screenshots of every screen (desktop light, desktop dark, 390 px) in `logs/sample/ui_*.png`, the `/billing` fields and how each is recomputed, and any spec item not done with the reason.
