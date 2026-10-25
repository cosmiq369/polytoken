# Architecture and data onboarding validation

The app now exposes How it works through the information button and sidebar. Its
inline SVG is the same source as `web/architecture.svg` for presentation reuse.
Meterless runs as in-repo Python against a pinned reference specification. Standard
model-fit investigations use local cached candidate tokenizers and dated SQL price
quotes; live summaries go to NVIDIA. The optional quality experiment is separate.

The launcher gives an actionable restart message if its options endpoint is absent.
A fresh demo process loaded candidate models and launched Raitu through the real
POST/SSE flow. Opening architecture retained the replay. Browser checks covered
1080p light/dark, mobile overflow and the simulated stale-server failure.

The canonical add-data skill and identical Claude copy route conversion to the
user's own folder, keep it local, require consent before drafting English, and keep
review pending. `validate-sample` reuses the launcher parser and reports counts or
structural diagnostics without conversation text. The bundled template passed
(two rows, one chat); deliberately malformed input failed with a row-specific error.

Validation:
- `.venv/bin/python -m pytest -q`: **291 passed, 8 live tests skipped**, 190.71 s.
- `NODE_PATH=/Users/mohan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node web/check-architecture.cjs`: passed against a fresh `polytoken serve --demo --port 8011`.
- Focused sample/launcher suite: 27 passed.
- `git diff --check` and source/browser syntax checks: passed.
- All tracked Markdown links to ignored local presentation directories removed.

Video, deck, audio and internal prompt directories are ignored and untracked; their
files remain local. The submission checklist remains local. Public video URL:
PENDING UPLOAD. The deck is submitted through the hackathon form.

Historical objects were not rewritten. Unique uncompressed historical blob sizes:
video 41,584,294 bytes (39.66 MiB), deck 2,631,306 bytes (2.51 MiB), prompts 101,878
bytes (0.10 MiB). Total 44,317,478 bytes (42.26 MiB). These are object contents, not
reclaimable pack-size estimates. Old objects remain reachable in history.

Evidence: `logs/sample/architecture_validation.jsonl`; plain app screenshots in
`docs/images/how_it_works_dark.png` and `docs/images/how_it_works_light.png`.
Live uploaded-data integration has not yet been verified by this change.
