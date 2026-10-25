# PROMPT-05 checkpoint: PolyToken interface

Implemented in `/Users/mohan/BuildingWealth/PolyToken/.cache/worktrees/ui` on
`feat/ui`, based on the requested `origin/feat/agent` commit `d4d3251`.
Implementation commit: `a3c6d50`.

The page provides Ask, Investigation, Report and Evidence views with no build,
framework, CDN or npm dependency. The only backend change is a final static mount
in its own function. Existing API endpoints retain precedence. No investigation,
checker, quality protocol, dependencies or company data were changed.

Ask loads companies through the API and submits optional overrides. Investigation
shows the nine recorded steps, tool names, why sentences, findings, live evidence,
call/time telemetry and background progress. Native SSE reconnects with event IDs;
report polling also handles the background job's running-to-complete transition.
Report shows checked ratios and intervals, billed composition, quoted savings,
quality and optional A/A controls, timing spread, dropped claims, limitations and
signed Markovian accounting. Evidence includes the exact claim, formula recipe,
input IDs, provenance, raw payloads and transitive source links.

Saved report / JSONL import works locally in the browser. Unknown fields are
ignored; unverified, dropped and nonfinite values do not become display metrics.
Missing data remains missing. Fix ranking and verdicts remain the server's.
Negative values keep their sign. Source text is escaped. No model calls are
made by the UI tests or saved-file workflow.

## Verification

Exact final full-suite command, run from the UI worktree:

```sh
UI_SCREENSHOTS=1 PYTHONPATH=src /Users/mohan/BuildingWealth/PolyToken/.venv/bin/python -m pytest -q
```

Result: **184 passed, 8 skipped in 15.74 seconds**. The skipped tests are the
existing opt-in live checks: 2 agent, 3 data and 3 service tests.

The browser test uses the already-installed Playwright and Chromium
151.0.7922.34, intercepting all HTTP requests from recorded fixtures. It parses all
six saved report fixtures and checks native SSE replay, POST overrides, report
polling, missing evidence, partial reports, optional A/A claims, dropped and
unverified claim exclusion, HTML escaping, structured query previews, error
recovery, and all four screens at 390 px in light and dark themes. Visible text
checks enforce a 4.5:1 contrast floor. Desktop and mobile screenshots were also
visually inspected; evidence cards retain their content when the list scrolls.

Other successful commands:

```sh
node --check web/app.js
node --check web/check-ui.cjs
git diff --check
```

A secret-pattern scan passed for all seven implementation/test text files.
The final validation result and screenshot hashes are in `ui_validation.jsonl`.

## Screenshots

All use saved Samudra run `ec57418c-2024-44f4-b092-686629999043`, its saved event
stream, and the v1/v2 World Model archives. The Ask company responses are
intercepted from archived company configuration, not invented sample values.

- [Ask](ui_ask.png)
- [Investigation](ui_investigation.png)
- [Report](ui_report.png)
- [Evidence](ui_evidence.png)
- [Report at 390 px](ui_report_mobile.png)
- [Evidence at 390 px, dark](ui_evidence_mobile_dark.png)

## Deviations and integration notes

- The API has no checked transcript totals. The Transcript toggle explains the
  missing measurement; the browser does not derive or fabricate it.
- Events contain call counts and time but no call ceilings. Budget meters show
  the sourced numbers and indeterminate bars with an explicit missing-ceiling
  label instead of hardcoded server limits.
- Saved v1/v2 reports have no A/A floor. The UI shows not measured and accepts
  PROMPT-04C's optional `quality/aa/{passed,judged}` and interpretation fields.
- Evidence records may omit their original run ID. The report's run is shown
  separately, and the missing evidence-run field is labelled, not filled in.
- The interface is served from a source checkout. Standalone wheel packaging is
  outside the owned scope; `web/` must accompany the source tree.
- The requested `claude-mem` work-state tools were not exposed in this session;
  the checkpoint and validation state are recorded under `logs/sample/` instead.

No merge into `feat/agent` or `main` was performed. PROMPT-04C changes were not
cherry-picked into this isolated branch. This is the PROMPT-05 stop point.
