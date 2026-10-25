# PROMPT-05B checkpoint: The Token Ledger

Completed in `/Users/mohan/BuildingWealth/PolyToken/.cache/worktrees/ui`, continuing
`feat/ui` from `21e4050`. Implementation commits:

- `ae09806`: checked USD billing projection, currency reference/compatibility
  loader, and local token inspection endpoints.
- `6487eaf`: Token Ledger UI, scenario/currency receipts, copied full specification
  and design references, schema documentation and expanded tests.

The restored PROMPT-05 and PROMPT-05B were copied byte-for-byte from the main
checkout. `docs/design/reference/` is committed as reference material. The agent,
tools and checker files have no changes relative to the branch foundation.
PROMPT-04C work on `feat/agent` was not merged or cherry-picked.

## Result against the eleven gaps

| Requirement | Result |
| --- | --- |
| Currency | Extensible sourced rate list; original INR value/timestamps preserved; `/currencies`; USD/INR and future rows; remembered selection; shown source/date and a currency receipt |
| Headline and strip | Plain-language finding; canonical USD monthly, per-1,000-conversation and per-reply costs; money/percent language tax; measured token multiplier with English at one |
| Resends | Checked billed/transcript composition, resend factor, identical system-prefix input share, and a real median-conversation staircase |
| Fix ladder | Independent today-to-after SVG waterfalls; tested/estimated states; quality/status/reason retained; negative savings in a separate “Would cost more” group |
| Model comparison | Every measured tokenizer; verified provider price or explicit “no verified price”; cost/conversation, paired multiplier and weighted fragment share; non-zero intervals only |
| What-if | Volume and separate input/output price multipliers; reprices only checked token splits; visibly hypothetical; reset; receipt with formula/inputs; checked headline remains unchanged |
| Token strip | Company-chat default plus paired English; editable text; eight local tokenizer rows; hatched fragments, counts and whitespace-word/fragment ratios; unknown IDs and filesystem paths refused |
| Quality | Two 20-dot strips with the eighteen-of-twenty line; recorded pair order when available; explicit missing A/A on older reports; interpretation and pending native review retained |
| Dropped claims | Readable names and reasons; original ID and checker record kept in the receipt |
| Reply time | Original/changed hosted model names and stand-in relationship displayed beside medians and spread |
| Token Ledger design | Paper/turmeric/indigo, tabular monospaced figures, serif headings, verdict stamps, trilingual tagline, hand-authored SVGs, true dark mode, mobile and keyboard controls |

The headline uses **89.2% of quoted cost**, rather than copying the illustrative
96% example: the source actually measures 96.3% of billed tokens but different
input/output prices produce an 89.2% cost share. The distinction is intentional.
The whole-chat native/English token multiplier is 9.3784; the separate system
prompt ratio is 9.4882. Each has its own receipt.

## Billing fields and checking

The full endpoint contract and field-by-field formulas are in
[`web/BILLING_SCHEMA.md`](../../web/BILLING_SCHEMA.md). The archived response
summary [`ui_5b_billing_sample.json`](ui_5b_billing_sample.json) contains all **303**
projection claims for the saved Samudra run, with formulas and input IDs.

`billing_view.py` authenticates source hashes/provenance and transitive support.
The existing `Checker.check()` recomputes the source baseline and an explicitly
sourced English selector baseline. `billed_tokens()` reconstructs each completed
request; `cost_usd()` independently reconciles the resulting native and English
USD bills with those checked baselines. The projection pass is repeated before
custom claims are emitted. Financial report claims run through their original
checker operations before their savings form an after-cost. Alternative
input/output splits must reconcile to that after-cost before what-if uses them.
The agent checker's operation allowlist is unchanged.

For the archived Samudra v2 run, the checked view gives:

- Monthly content cost: USD 116.02034.
- The same content in measured English: USD 12.60196.
- Language tax: USD 103.41838, or 820.6531% above English.
- System prompts paid per conversation: 1.98.
- Identical system-prefix share of input: 0.9765306758.

These are quoted-provider scenarios from recorded SQL evidence, not invoices.
USD is canonical in the new view. Original legacy INR report files remain intact;
conversion back to USD uses each claim's original FX receipt. Display conversion
then uses the selected sourced rate.

Audit, projection recipes, derived English evidence and token measurements go to
`logs/billing*.jsonl`, `logs/currencies.jsonl` and `logs/token_strip.jsonl`.
The curated checkpoint, screenshot hashes and validation result are in
[`ui_5b_validation.jsonl`](ui_5b_validation.jsonl).

## Exact verification

From the UI worktree:

```sh
UI_SCREENSHOTS=1 PYTHONPATH=src /Users/mohan/BuildingWealth/PolyToken/.venv/bin/python -m pytest -q
```

**188 passed, 8 skipped in 72.62 seconds.** Skips are the existing opt-in live
checks: two agent, three data and three service tests. No provider requests were
made. An earlier targeted run of `tests/test_ui_static.py` also passed all six
checks. The final full run includes its latest cache-tampering and receipt checks.

The production projection code rebuilds six saved-report browser fixtures.
Chromium 151.0.7922.34 then intercepts every request locally. Checks cover exact
hand-computed billing arithmetic, tampered/missing support, cache invalidation
under a reused evidence ID, FX refusal rules and compatibility, USD/INR/future
currency switching and persistence, negative-saving placement, interval rules,
readable dropped claims, local lossless token boundaries, optional A/A dots,
what-if changes/reset/receipts, escaping, partial reports, SSE replay/deduplication,
polling and failure recovery. Every screen passes page-overflow and 4.5:1 visible
text contrast checks in all four size/theme combinations.

Other successful checks:

```sh
node --check web/app.js
node --check web/check-ui.cjs
git diff --check
git diff --name-only d4d3251 -- src/polytoken/agent src/polytoken/tools src/polytoken/checker.py
```

The protected-path diff is empty. A secret-pattern scan passed for 21 changed
implementation/test/reference text files. All five screen types were visually
inspected as well as checked in the browser.

## Screenshots

All use saved Samudra run `ec57418c-2024-44f4-b092-686629999043`, its recorded
World Model/event sources and actual cached tokenizer files. No fabricated A/A
result is used in these screenshots; the optional A/A rendering test is explicitly
test-only. The original PROMPT-05 screenshots are preserved separately.

| Screen | Desktop light | Desktop dark | 390 px light | 390 px dark |
| --- | --- | --- | --- | --- |
| Ask | [PNG](ui_5b_ask_desktop_light.png) | [PNG](ui_5b_ask_desktop_dark.png) | [PNG](ui_5b_ask_mobile_light.png) | [PNG](ui_5b_ask_mobile_dark.png) |
| Investigation | [PNG](ui_5b_investigation_desktop_light.png) | [PNG](ui_5b_investigation_desktop_dark.png) | [PNG](ui_5b_investigation_mobile_light.png) | [PNG](ui_5b_investigation_mobile_dark.png) |
| Report | [PNG](ui_5b_report_desktop_light.png) | [PNG](ui_5b_report_desktop_dark.png) | [PNG](ui_5b_report_mobile_light.png) | [PNG](ui_5b_report_mobile_dark.png) |
| Token strip | [PNG](ui_5b_tokens_desktop_light.png) | [PNG](ui_5b_tokens_desktop_dark.png) | [PNG](ui_5b_tokens_mobile_light.png) | [PNG](ui_5b_tokens_mobile_dark.png) |
| Receipt | [PNG](ui_5b_evidence_desktop_light.png) | [PNG](ui_5b_evidence_desktop_dark.png) | [PNG](ui_5b_evidence_mobile_light.png) | [PNG](ui_5b_evidence_mobile_dark.png) |

[Report summary viewport](ui_5b_report_summary.png).

## Data limits and deviations

All eleven requested gaps are implemented. The following absences are preserved
rather than filled:

- Older reports have no A/A experiment. They show not measured; optional newer
  claims and interpretation fields are supported and tested.
- Tokenizers with no verified input/output price show no verified price.
- Inseparable reasoning usage remains unsupported throughput, with readable
  rejection reasons. The named stand-in's visible TTFT/latency remain sourced.
- API events still supply no budget ceilings; the gauges show sourced counts and
  time without invented caps or percentages.
- Archived version-1 sampled-last-turn experiments cannot establish whole-chat
  after-costs. They retain an explicit comparison reason. What-if cannot reprice
  an alternative without a checked/reconciled input/output split.
- Source observations and native translation/quality review remain pending where
  the underlying report says so. A cheap estimate is not promoted to a safe fix.
- The UI is a source-checkout service. Standalone wheel packaging remains outside
  this task. No build or npm step was introduced.
- `claude-mem` work-state tools were not exposed in this session; completion state
  is recorded in the JSONL validation checkpoint instead.

This is the PROMPT-05B stop point. Only `feat/ui` is prepared for push; no merge,
tag or release is part of this checkpoint.
