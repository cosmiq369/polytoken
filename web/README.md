# The Token Ledger

PolyToken's source-checkout interface answers five billing questions: what we
pay, the extra cost above English, the repeated content behind it, which change
preserves meaning, and what changes with volume, price or model.

Plain HTML, CSS and JavaScript. No framework, build, CDN, chart library or npm
installation. Run `polytoken serve` from a configured source checkout and open
`http://127.0.0.1:8000/`. The final static mount exposes only `web/`; `.env` and
`logs/` are not mounted. Paper/turmeric/indigo styling, tabular figures, SVG charts,
verdict stamps, light/dark media support and keyboard controls follow the restored
Token Ledger spec under `docs/prompts/PROMPT-05-ui.md`.

The new routes and every projected field/formula are described in
[BILLING_SCHEMA.md](BILLING_SCHEMA.md). The investigation worker, agent/tools,
checker and saved report files retain their contracts. USD is canonical in the
billing view; legacy INR records remain exact in receipts. Only currency
conversion and clearly labelled what-if scenarios calculate business values in
the browser. Missing data stays missing.

## Saved investigations and receipts

On Ask, choose one `logs/sample/agent_*_report.json`. Add its event JSONL and World
Model JSONL to inspect steps and transitive raw evidence. Files stay in the
browser. The billing endpoint can also resolve curated archived report IDs from
its configured `logs/sample/` and derive a fresh checked view from recorded World
Model sources. A source unavailable to this server remains explicitly unavailable.

For Samudra v2 choose `agent_samudra_v2_report.json`, `agent_samudra_v2.jsonl`,
`agent_world_events.jsonl` and `agent_v2_world_events.jsonl` from `logs/sample/`.
Only matching investigation events appear. New billing claims carry direct
receipt inputs; imported World Model files supply reused/transitive records.
No provider generation occurs during saved-file review or token inspection.

Token inspection defaults to a native user turn from the billing snapshot, with
its paired English translation available. Only known cached tokenizer files are
used. The existing `indictax` library supplies encoding and fragment classification;
weights are never loaded. Partial-character tokens are hatched and their raw
labels are available. Every returned display span joins back to the input.

## Verification and screenshots

Run pytest from this checkout with its source on `PYTHONPATH`. The endpoint tests
check exact hand-computed billing examples, FX compatibility and refusal rules,
tampered/missing evidence, negative savings, local token boundaries and API route
precedence. Live/provider tests remain opt-in.

When Node and Playwright are already installed, the browser test first builds
fixtures through the production Python projection code. It intercepts every HTTP
request: no Zetaris or provider calls. It exercises all saved reports, future
currency rows, USD/INR persistence, after-cost grouping, meaningful intervals,
readable dropped claims, A/A and A/B strips, what-if reset, source escaping,
missing-data recovery, native SSE replay and polling. Every screen is checked at
1440 px and 390 px, in both themes, for page overflow and 4.5:1 text contrast.

`UI_SCREENSHOTS=1` on pytest captures the full matrix as
`logs/sample/ui_5b_<screen>_<desktop|mobile>_<light|dark>.png`, plus a report summary
viewport. Existing PROMPT-05 screenshots remain as the historical checkpoint.
A standalone browser run can use `web/prepare-ui-fixtures.py <directory>` with
`PYTHONPATH=src`, then set `UI_BILLING_FIXTURES` and run `node web/check-ui.cjs`.
Use `NODE_PATH` for an existing nonstandard Playwright installation; no npm step
is needed. Empty local tokenizer caches produce explicit unavailable rows.

PROMPT-06 refreshes the screenshot matrix using the contextual v3 Samudra report.
INR is the initial demo currency. Byte fragments show hex bytes, grouped by source
character. Saved evidence imports accept `.jsonl.gz`; decompression stays local.
`record-demo.cjs` performs a real UI investigation against a running local server
and archives its report/events and screen captures. It makes live model calls;
run it only when intentionally recording a new investigation.

## Agent console (PROMPT-07)

Run `polytoken serve --demo` for the offline console and open
`http://127.0.0.1:8000/`. Samudra and Swara are pinned first in the saved history.
Choose **Run a demo investigation**, or select a saved run. Replay supports 1×,
4×, 16×, pause, Stop, restart and scrubbing. The server rechecks archived claims
against their World Model evidence. Live investigations require restarting without
`--demo`; Stop signals the same cancellation guard used by provider retries and
background jobs. Settings saves a light, dark or system theme. Alt+R runs/replays,
Alt+S stops, Alt+1–7 switches run tabs and Alt+8 toggles raw events.

`console.js` uses the same event state as live SSE. The investigation desk shows
current work, a highlighted stage path, verified findings and grouped services.
Navigation stays in place while content scrolls. A neutral palette distinguishes
activity, testing, verification and failures. Billing keeps its focused subviews. New event fields and routes are in
`docs/REPORT_SCHEMA.md`; design decisions are in `docs/design/CONSOLE.md`.

The full pytest suite runs both `check-ui.cjs` (existing billing regressions) and
`check-console.cjs` (replay and console acceptance). The latter intercepts all
requests; its live Stop case is explicitly a fake run with nested SQL spans.
`record-console.cjs` instead captures the **real offline server**, with no mocked
API replies. Use the existing Playwright `NODE_PATH` described above. It writes
72 screenshots under `docs/images/console_*.png` and `console_replay.webm`, and
records provenance in `logs/sample/console_validation.jsonl`. The video contains
the curated 34-second Samudra run at 4× followed by a tour of its checked results.
Legacy archives predate physical spans, so they disclose unavailable timings.

The console regression checks also cover the Swara quality-review stage, fixed
navigation at 320–1280px, mobile stage visibility, trace keyboard focus through
event updates, currency captions, review-required outcomes, reduced motion and
640×475 zoom-equivalent reflow. Screenshot proof includes Swara in progress and
scrolled navigation in both themes and viewport sizes.
