# PROMPT-09 completion — 25 October 2026

The final submission deck and narrated app demo are ready for Mohan’s review. Video upload, repository visibility and form submission remain manual steps in SUBMIT_CHECKLIST.md (local submission material).

## Deliverables

- 1080p narrated MP4 (local submission material) — **2:49.28**, H.264 + AAC, 25 fps; approximately 14 MB.
- SRT captions (local submission material) — 45 aligned cues, also burned into the video.
- Video contact sheet (local submission material) — final frames every ten seconds.
- Ten-slide PDF (local submission material) and editable PowerPoint (local submission material).
- Slide PNG exports (local submission material) and deck contact sheet (local submission material).
- Technical manifest (local submission material), scene/audio files (local submission material), and checked deck values (local submission material).

The video has a two-second opening card and 0.25-second crossfades. At least **86.7%** is the real local app; deck overlays occur only in the hook and close. The app is dark, uses INR and replays recorded investigations at **2×**. Final measured integrated loudness is **−16.01 LUFS**, with **−3.54 dBTP** true peak.

## Scene timings

| Scene | Narration audio | Screen clip |
| --- | ---: | ---: |
| S01 — hook | 14.66s | 17.86s |
| S02 — the cause | 17.63s | 22.13s |
| S03 — the agent at work | 31.85s | 35.05s |
| S04 — the answer | 34.38s | 37.58s |
| S05 — four companies | 18.47s | 21.67s |
| S06 — trust | 14.95s | 18.15s |
| S07 — close | 13.37s | 16.57s |

Clip durations include pauses to read the evidence. Crossfades overlap adjoining clips; the opening card adds two seconds. Speech uses the configured ElevenLabs cloned voice, Multilingual v2 and a pitch-preserving pace adjustment. Character timings were adjusted with the audio.

## Evidence and fixes

All four reports were authenticated and recomputed before the deck was built. The 12/12 addendum checks pass. Raitu’s 2.61× comparison, 5.03× versus 1.35× English tokens and ₹139 versus ₹363 monthly amounts come from checked claims and the dated FX receipt. [Evidence preparation](../scripts/video/prepare_evidence.py).

The reference token-strip example independently encodes to 102 Llama tokens and 17 Sarvam tokens. Its illustrative Tenglish rendering has 19 Llama tokens, against 17 English tokens. The sentence is from historical fictional Samudra data; it is not a Raitu workload measurement. [Token receipts](../logs/sample/video_token_strip.jsonl).

The narration corrects “real conversations” to fictional company conversations and “one federated query” to federated SQL. The app now offers a 2× replay speed and displays explicit model-fit cost and token-ratio equations in receipts. Voice latency remains unverified, quality needs sample verification, and monthly costs remain content estimates rather than invoices.

## Verification

| Exact command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | **241 passed, 8 skipped in 173.12s** on the final UI; the eight live tests require explicit opt-in. |
| `.venv/bin/python scripts/video/prepare_evidence.py` | Four reports authenticated and recomputed; **12/12** addendum checks passed. |
| `PYTHONPATH=/tmp/p09-python .venv/bin/python /Users/mohan/.codex/plugins/cache/claude-cowork/anthropic-skills/1.0.0/skills/pptx/scripts/office/validate.py docs/deck/PolyToken_deck.pptx` | All validations passed. |
| `.venv/bin/python scripts/video/check_frames.py` | Contact sheet + 17 full-resolution frames: **18 images**, zero key-text hits. |
| `.venv/bin/python scripts/ship_secret_scan.py` | **1,428 reachable objects** plus tracked and non-ignored worktree files: zero configured secret values or credential-prefix hits. |
| `ffmpeg -v error -i docs/video/PolyToken_demo.mp4 -f null -` | Complete audio/video decode passed. |
| `ffmpeg -hide_banner -i docs/video/PolyToken_demo.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -` | Final input loudness **−16.01 LUFS**. |
| `git diff --check` | Passed. |

The receipt recording asserts the explicit equation is present. The recorder restricts requests to the local app origin, asserts token counts and catches page errors. Slides were visually inspected; title wrapping and the comparison-table spacing were corrected. Video review verified the key metrics, captions and receipt, and prompted a timing retake of the token-strip scene. OCR is a sampled-frame check, not a claim that every video frame was OCR-scanned.

[Validation audit](../logs/sample/video_deck_validation.jsonl) · [Production audit](../logs/sample/video_production.jsonl) · [History secret scan](../logs/sample/ship_secret_scan.jsonl).

## Mohan’s review

Check cloned-voice pronunciation and pacing, the fictional-data disclosure, and the cost/quality/latency caveats. Then upload the MP4, paste the public URL into README, SUBMISSION and metadata, make the repository public and submit the deck PDF. The public video URL is deliberately still empty.

The local demo is left running with `.venv/bin/polytoken serve --demo` at [127.0.0.1:8000](http://127.0.0.1:8000). Release branch: `release/video`; publication fast-forwards `main`. Existing unrelated untracked files were left untouched.
