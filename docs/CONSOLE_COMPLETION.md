# PROMPT-07 completion

Branch: `feat/console`, created from local `main` after fast-forwarding `feat/ship`.
No `fix/live-run` branch was present. Push targets only `feat/console`.
The push is currently blocked by automatic approval review pending direct user
approval of `https://github.com/cosmiq369/polytoken`; all commits are local.

## Changes

- `9f3b90a`: causal tool, SQL and model telemetry; checked live findings; qualitative
  planner explanations; cooperative Stop; price-read recovery; offline archive
  discovery and evidence-verified replay API; backend acceptance tests.
- `2c96d5f`: developer console shell, service circuit, nested trace, run status and
  clock, budget gauges, event tail, persistent theme, keyboard shortcuts, history,
  original-time replay and scrubbing. Existing billing, currency, quality, token
  and receipt renderers are preserved behind focused run tabs. Browser coverage
  and the reproducible capture script are included.
- The final proof commit contains this report, 64 screenshots, the recording and
  `logs/sample/console_validation.jsonl`.

The design rationale is [CONSOLE.md](design/CONSOLE.md): slate/blue surfaces,
cyan activity and evidence, explicit error states, 14px system sans and monospace
figures. The service circuit is the primary view; billing uses focused subviews
instead of a long report. No CDN, build step or new dependency was introduced.

## Validation

- `.venv/bin/python -m pytest -q` — **219 passed, 8 skipped in 143.01s**.
  All skipped tests are explicitly opt-in live NVIDIA/Zetaris/data checks.
- `.venv/bin/python -m pytest tests/test_console.py tests/test_agent.py -q` —
  **71 passed in 11.84s**.
- `node web/check-ui.cjs` with generated `UI_BILLING_FIXTURES` and the bundled
  Playwright `NODE_PATH` — passed across 12 saved reports, retained billing
  assertions, currencies, receipts, what-if, quality strips, token boundaries,
  SSE/polling and failure recovery. This command also runs inside full pytest.
- `node web/check-console.cjs` with the same environment — passed replay clocks,
  ordered observed edges, backward scrubbing, verified findings, nested SQL spans,
  fake-live Stop, shortcuts, all views, 1280/390px, dark/light contrast and overflow.
  This command also runs inside full pytest.
- `node --check web/app.js`, `node --check web/console.js`, `git diff --check` — passed.
- Configured-secret and provider-prefix scan of tracked/unignored working files —
  **367 files checked, zero hits** (recorded in the console validation JSONL).

## Proof and running demo

`polytoken serve --demo` is left running at <http://127.0.0.1:8000/>. It uses archived
Zetaris evidence and blocks live generation. Samudra and Swara are first in history.

[Replay recording](images/console_replay.webm): approximately 72 seconds. The
curated Samudra execution is about 34 seconds of source time, played at 4×,
followed by an inspection of the results. It was recorded against the real offline
API; no response mocks or live provider calls were used. Capture command:

```sh
NODE_PATH=/Users/mohan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node web/record-console.cjs
```

All 64 screenshots are `docs/images/console_<view>_<desktop|mobile>_<dark|light>.png`.
Views: settings, companies, history, activity, trace, overview, billing,
quality, evidence, tokens, billing_replay, billing_models, billing_scenario,
billing_compression, receipt and events.

Representative captures:

- [Activity, dark](images/console_activity_desktop_dark.png)
- [Overview, light](images/console_overview_desktop_light.png)
- [Quality, dark](images/console_quality_desktop_dark.png)
- [Receipt, light](images/console_receipt_desktop_light.png)
- [Mobile activity](images/console_activity_mobile_dark.png)

## Explicit limits

Existing saved runs predate physical call spans. Replay labels their tool
observations as legacy and their call timing as unavailable; it does not invent
latencies. Fresh live runs emit full spans. The new physical-span UI and Stop are
verified with deterministic fake live calls, not a new billed provider experiment.
Stop waits for an in-flight bounded call to return, then prevents subsequent
attempts. Legacy budget ceilings remain “not recorded” rather than being inferred
from today's limits. Native-review and quality limitations remain visible.

The pre-existing untracked VIDEO_SCRIPT and prompt files were left untouched.
