# PROMPT-06 shipping checkpoint — 25 October 2026

The approved integration is pushed to `main` at **a5b4bec**. `feat/agent` was fast-forwarded into main, the untracked prompts/design references were committed, and `feat/ui` was merged without conflicts. The API retains localhost CORS, SSE events, billing/token routes and the static mount. The two completed `.cache/worktrees/` checkouts were clean and removed. Shipping changes are on **feat/ship**, not merged into main. No tags, releases or visibility changes were made.

## Implementation commits

- `30fe971` — Clarify v3 billing evidence and render readable byte tokens.
- `b5cb146` — Add offline contract scoring and compressed demo archives.
- `6c2ee44` — Prepare judge submission with recorded demo and evidence.
- `809a1b2` — Include the gzip evidence reader and regression for latest demo selection.
- A final evidence-only commit records the completed checks and screenshot refresh. Its hash is reported in the final handoff.

## UI review fixes

All seven review items are implemented. The refreshed `ui_*.png` screenshots use the authenticated Samudra v3 report: A/A 7/20, A/B 3/20, both threshold lines, a single INCONCLUSIVE stamp and the prescribed interpretation. Money and billed-token shares have explicit labels; the cost comparison is 9.2× English with its money figure. The UI explains that answers have a higher quoted token price. Estimates have one status stamp. Resends are compact horizontal system/history/new-user stacks with a cumulative-input line and one repeated-system label. Byte fragments display hex cells under their source character. INR is the initial demo currency, preserving an explicit remembered selection.

Desktop and 390 px light/dark browser checks cover all screen types, overflow, contrast, source receipts, failure recovery and gzip evidence import. Prior screenshot versions remain in Git history. The screenshot hash manifest is in [ship_checkpoint.jsonl](ship_checkpoint.jsonl).

## Contract result

`polytoken score` is offline and is never imported by the agent. It authenticates source closures and replays numeric claims before selecting and scoring the latest complete run. The output records claim IDs, source/report hashes, diagnostic chat IDs and limits. Missing or altered evidence fails the evaluation instead of producing a passing score.

| Company | Q1 cost | Q2 source | Q3 speed | Q4 fixes | Top finding | Expected fix | A/A | A/B | Native review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Samudra | partly | yes | partly | partly | pass | inconclusive | 7/20 | 3/20 | pending |
| Swara | partly | yes | partly | partly | pass | inconclusive | 3/20 | 1/20 | pending |

The literal 18/20 A/B verdict fails for both. Both controls also fail, so the interpretation is **“the bar cannot be met by this judge and stand-in model; result inconclusive.”** No result was changed to fit the contract. Missing prices/cost intervals and the absence of a deployed-model native/English speed experiment prevent full coverage.

Samudra A/A has **3/20 byte-identical reply pairs**; **11/13** different verdicts contain only added material claims. Swara has **0/20 identical pairs** and **13/17** added-only different verdicts. These model classifications do not establish human semantic correctness. [Complete score and evidence IDs](contract_score.md) · [JSONL](contract_score.jsonl).

All scored limits are respected. Samudra's latest run used reasoning/judge/hosted/SQL **12/0/0/4**, with **17.49 s** reasoning and **9.99 s** background work. Swara used **16/24/8/4**, with **27.16 s** reasoning and **297.71 s** background work. The score retains separate limits for reasoning, judging, hosted attempts and SQL, plus both wall deadlines.

## Real UI demo

Samudra run **9a5b36c1b257413388f5941e6ffcfeed** completed through `polytoken serve` and Chromium, without request interception. The report contains no recommended fix. It reconstructed **₹11,015.34 → ₹2,229.74** at the recorded monthly volume, retaining the inconclusive quality result and cached-timing limitation.

The reasoning and SQL were new; generation, all 40 valid judgments and speed evidence were reused under the existing authenticated cache identities. The demo is not an independent quality replication. Physical-call and SQL logs reconcile exactly to the reported counts. [Events](demo_samudra.jsonl) · [Report](demo_samudra_report.json) · [Compressed evidence closure](demo_samudra_world_events.jsonl.gz) · [Screenshots](../../docs/images/). The closure contains 223 evidence events: 22,555,542 uncompressed bytes, 796,521 gzip bytes. The screenshots were subsequently rerendered from that same saved report with the final UI; no second investigation was launched.

## Exact validation

All commands below ran from the applicable checkout root.

| Command | Result |
| --- | --- |
| `UI_SCREENSHOTS=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q` | **205 passed, 8 skipped**, 146.76 s |
| `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q` | **206 passed, 8 skipped**, 136.74 s (final implementation) |
| `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q -m live` | **8 passed, 205 deselected**, 12.26 s |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_score.py tests/test_ui_static.py::test_byte_labels_reconstruct_telugu_utf8` | **4 passed**, 15.39 s |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/polytoken score` | Both complete reports replayed; both top findings pass |
| `node --check web/app.js`; `node --check web/check-ui.cjs`; `node --check web/record-demo.cjs`; `git diff --check` | Passed |

Fresh clone `/tmp/polytoken-ship-final-VNNcZj` at `809a1b2`:

```sh
uv venv .venv
uv pip install '.[dev]'
PYTHONDONTWRITEBYTECODE=1 HF_HOME=/Users/mohan/BuildingWealth/PolyToken/.cache/huggingface HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q
```

**206 passed, 8 skipped in 139.36 s**, on Python 3.13.15. Both `polytoken` and `indictax` imported from the new environment's `site-packages`; Git dependency provenance matches the pinned public commit. No `.env` was copied. Existing tokenizer cache files and the available Playwright installation were reused for offline browser verification. The final commit changes only evidence/documentation/screenshots, not the tested implementation.

The initial browser launch was denied by the sandbox. Elevated Chromium execution passed. Development test failures caused by using a v2-only dropped-claim assertion on v3, and by mixing Playwright paths/buffers, were corrected; the final full runs above pass. Final commit review also caught an omitted gzip-reader change; it was committed with a latest-demo regression, and both full suites were repeated on that exact implementation.

## Release scan and reviewer rulings

[History and working-tree scans](ship_secret_scan.jsonl) found **no configured credential values** and **no provider-key strings**. `docs/prompts/` is excluded only from provider-prefix pattern matching; it is included in the configured-secret-value check. The prior audit files themselves quote the bare search prefix; these have no credential suffix and are explicitly recorded as nonsecret references. Nonsecret configuration values (public endpoints, model identifier, RPM and database username) occur in history and are counted separately. No value was printed by the scanner.

The reviewer accepted the original World Model archives of **15,921,942**, **15,536,266** and **40,470,818 bytes**. They remain byte-identical to main and are listed in the README. There are no other committed files over 5 MB; the new large evidence closure is gzipped. Ignore checks confirm `.cache/`, `.venv/` and non-sample runtime logs are excluded. No history was rewritten.

## Submission and remaining human steps

[README](../../README.md), [metadata](../../metadata.json), [MIT licence](../../LICENSE), [standalone architecture](../../docs/images/architecture.svg) and [submission prose](../../docs/SUBMISSION.md) are ready. The sponsor explanation is 378 words and the project summary exactly 150 words. Local document links and SVG XML validate. Pre-existing experiment 01 result files were copied unchanged as declared evidence; their token ratios were recomputed from their counts, without copying harness code or changing the sibling repository.

Mohan still supplies the video URL and decides when to publish the repository. Native Telugu/Hindi review is pending; no approval is implied by shipping this checkpoint. The runtime requires a source checkout even after a non-editable install; asset discovery was corrected for that supported workflow. The agent, tools and deterministic checker were not changed. The claude-mem work-state tools were unavailable, so checkpoint state is recorded in JSONL. No subagents were used.
