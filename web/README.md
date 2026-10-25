# PolyToken interface

Plain HTML, CSS and JavaScript; no build, framework, CDN or npm installation.
From a source checkout, run `polytoken serve` and open `http://127.0.0.1:8000/`.
The static mount is last so existing API routes keep precedence. Only `web/` is
publicly served; neither `.env` nor `logs/` is mounted. The API static path resolves
relative to its source file, independent of the shell's working directory.

## Saved investigations

On Ask, select one `logs/sample/agent_*_report.json`. Optionally select its event
JSONL and World Model JSONL in the same file chooser. Supporting files can also be
added later. A World Model archive wraps each event in `world_event`; bare events
are accepted too. The file loader stays in the browser and makes no model calls.
Only events whose investigation ID matches the report are displayed. Saved files
retain their recorded checker verdicts; opening a file is not a fresh checker run.

For the curated Samudra v2 demonstration, select:

- `logs/sample/agent_samudra_v2_report.json`
- `logs/sample/agent_samudra_v2.jsonl`
- `logs/sample/agent_world_events.jsonl`
- `logs/sample/agent_v2_world_events.jsonl`

The older World Model archive supplies transitive evidence reused by the v2 run.
A missing source remains explicitly unavailable. Evidence views show the recipe,
its named source IDs, provenance, raw payloads and links to supporting records.
Runtime budget and experiment counters open their original event JSON.

## Display contract and deliberate gaps

`docs/REPORT_SCHEMA.md` is authoritative. Claims are selected by exact ID with
`verified: true`, finite numeric values and nonempty evidence IDs. Dropped claim
IDs take precedence. Tokenizer discovery strips anchored prefixes/suffixes, so
IDs containing `/` remain intact. Missing values are never coerced to zero.
Formatting uses `Intl.NumberFormat`; bar widths only encode existing values.
Fix ordering and statuses come from the report, not a new browser calculation.
Unrecognized fields are ignored. All source text is escaped before rendering.

The optional PROMPT-04C fields `quality/aa/{passed,judged}` and
`quality_interpretation` are supported. Their absence in older reports is shown as
not measured. Quality appears only on the fix with experiment evidence, so other
hypotheses do not inherit the tested fix's verdict. The denominator is the actual
checked judged count, including incomplete samples. Stand-in and pending native
review labels remain visible.

The current API does not provide checked transcript totals or call ceilings.
The Billed / Transcript control therefore explains the missing transcript claims;
it does not fabricate totals from billed counts. Budget meters show recorded
counts and elapsed/remaining seconds, with an indeterminate bar and an explicit
missing ceiling. The UI does not hardcode server limits. Provider aliases are not
silently mapped to tokenizers; the selected tokenizer is explicitly labelled.

The screenshot harness uses saved source records for company configuration and
intercepts every request. It does not run Zetaris or NVIDIA calls. The final page
has no test harness dependency. Deployment as a standalone installed wheel is
outside this source-checkout interface task; `web/` must accompany the checkout.

## Checks

Run the full pytest suite from this checkout with its Python environment. The
static route test is always run. With Node and Playwright already installed, the
browser test runs `node web/check-ui.cjs` and parses every saved report fixture,
including archived subdirectories. If Playwright is outside Node's search path,
set `NODE_PATH` to its existing `node_modules` directory. There is no npm step.

`node web/check-ui.cjs --screenshots` additionally writes `logs/sample/ui_*.png`.
It checks native SSE replay, POST inputs, report polling, explicit missing values,
partial reports, optional A/A data, negative savings, dropped/unverified claims,
HTML escaping, archive evidence, error recovery and both themes at 390px width.
It intercepts all HTTP requests; any external origin fails the check.
