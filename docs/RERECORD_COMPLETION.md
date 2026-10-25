# PROMPT-10B rerecord completion

Local presentation assets remain ignored and untracked. Steps 0–3 were committed in `b36e4fc` and `8b69dfa`. No speech was removed, rewritten, regenerated or sped up. The final supplied script supersedes earlier drafts.

## Verified presentation

Eight transcript-aligned clips; no material claim, number or qualifier mismatch. Final video: **176.6 seconds (2:56.6)**, 1920×1080 H.264/AAC, 50 burned-in caption groups plus SRT, 0.25-second crossfades. At least 86.0% is the actual app or recorded terminal output. The coding-agent prompt card is excluded from that minimum.

| Scene | Audio clip (s) | Screen scene (s) |
|---|---:|---:|
| S01 | 25.057 | 26.057 |
| S02 | 19.068 | 20.068 |
| S03 | 28.338 | 29.338 |
| S04 | 25.068 | 26.068 |
| S05 | 21.816 | 22.816 |
| S06 | 21.923 | 22.923 |
| S07 | 13.676 | 14.676 |
| S08 | 15.358 | 16.358 |

Source audio: 168.202 s; clip sum: 170.302 s, with 2.100 s of overlapping silent margins. Each scene adds 0.4 s head and 0.6 s tail. The old audio backup is intact. Only 80 Hz high-pass filtering and loudness normalization were applied; final integrated loudness is -16.77 LUFS.

Architecture is held for eight seconds with replay paused, then replay resumes at 2×. The S4 table includes “Quality: verify on your sample” for more than four seconds; the intentionally unspoken disclaimer is absent from captions. Native/Tenglish ratios 6.00×/1.12×, Raitu ₹139/₹363 and 2.61×, checked Q&A, refusal, and recompute recipe were visually checked in final frames.

Twelve deck slides were regenerated as PPTX, PDF and PNG. Package validation passed. The diagram comes from `web/architecture.svg`; Meterless is described as in-repo Python against the pinned reference specification. Four archived reports were recomputed; only the newly additive display-name field was normalized in an evaluation copy, leaving archives unchanged. All 12 model-fit addendum checks pass.

## Validation

- `.venv/bin/python -m pytest -q`: **291 passed, 8 skipped in 211.68s** before live verification; final run after the launcher status copy changed: **291 passed, 8 skipped in 191.37s**.
- Three Meterless conformance files with `-k "not indic_stable_ids"`: **29 passed, 1 deselected**. All three files without that filter: **30 passed** (includes the extra Indic regression).
- PowerPoint OpenXML validation: **All validations PASSED**; all 12 rendered slides inspected.
- Final SRT text exactly equals normalized final spoken text, including real spellings.
- History/worktree scan: **1,621 reachable objects; zero configured-secret or provider-prefix hits**.
- OCR: **25 images, zero secret-pattern hits** (contact sheet, 18 ten-second frames, six dedicated key frames).
- Fresh clone of `0075d28`: `uv venv .venv`, `uv pip install --offline --python .venv/bin/python '.[dev]'`, then `.venv/bin/python -m pytest -q`: **291 passed, 8 skipped in 197.26s**. No `.env` or presentation assets were copied.

## Historical assets and final checks

Untracking retains historical uncompressed unique blobs: video **41,584,294 bytes (39.66 MiB)**; deck **2,631,306 bytes (2.51 MiB)**; prompts **101,878 bytes (0.10 MiB)**; total **44,317,478 bytes (42.26 MiB)**. No history rewrite or force push.

Human review remains: pronunciations, scene cut points, caption timing and architecture legibility. Public video upload, repository visibility and hackathon form submission remain Mohan’s actions. Public video URL stays PENDING UPLOAD; the deck is supplied through the form.

After Steps 0–6 were committed and pushed (`8768240`), the bounded synthetic-template live upload completed: **141 claims independently rechecked, zero dropped, identical model-fit replay**. No application fixes or retries were needed. See [live-upload status](LIVE_UPLOAD_STATUS.md) for the exact scope and audit.
