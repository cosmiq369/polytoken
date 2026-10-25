# Narrated PolyToken demo

[Final video](PolyToken_demo.mp4) · [Captions](PolyToken_demo.srt) · [Contact sheet](contact_sheet.png) · [Technical manifest](manifest.json)

The recording uses the real offline PolyToken application at 1920×1080, INR and dark theme, replaying recorded investigations at 2×. The pointer highlight and cover/sponsor overlays are production aids; reports and API responses are not mocked. Each scene has a saved screen clip in `screen/` and a narrated MP3 with character-aligned timing metadata in `audio/`.

The voice is AI-generated with Mohan’s configured ElevenLabs cloned voice. Credentials and voice ID are read only from the ignored `.env`; they never enter the production files. Audio uses Multilingual v2, followed by a small pitch-preserving pace adjustment and final loudness normalization. [Narration and evidence notes](../VIDEO_SCRIPT.md).

The opening card is two seconds. Scene joins use 0.25-second crossfades. Captions are burned into a dark bottom band and also supplied as SRT. The contact sheet samples the final video every ten seconds; full-resolution samples in `review_frames/` support the OCR check.

## Reproduction

With `polytoken serve --demo` running and authoring dependencies available:

```sh
.venv/bin/python scripts/video/generate_narration.py
.venv/bin/python scripts/video/pace_audio.py
node scripts/video/record.cjs
python3 scripts/video/assemble.py
```

The recording command accepts an optional scene ID, such as `s04`, for a single retake. Initial setup is excluded using color synchronization slates. Raw takes are ignored by Git; trimmed scene MP4s are committed. The assembler needs FFmpeg, FFprobe, Pillow and macOS Arial fonts; no subtitle-filter build of FFmpeg is required. Caption PNGs and intermediate encodes are temporary files under `/tmp/polytoken-video-build/`.

Production requests, measurement receipts and validation live under `logs/sample/video_*.jsonl`. See [submission checklist](../SUBMIT_CHECKLIST.md) for the review and upload steps.
