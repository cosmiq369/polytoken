# Live uploaded-data verification

**Verified on 26 October 2026 (IST): one bundled synthetic Telugu chat template uploaded through the real launcher on the configured local stack.**

- Run: `d81b88c5df6c4f2dbc10399db14283b9`.
- Status: **complete**; 141 reported claims, all marked checked.
- Independent checker replay: **141 accepted, zero dropped**; model-fit decision exactly matches recomputation. The original report also dropped zero claims.
- Models selected: Llama 3.1 8B and Gemma 3 4B; local cached tokenizers and verified provider quotes. Candidate models were not called.
- Preflight: `polytoken doctor --live --port 8014` passed all 12 checks; PostgreSQL SELECT and both tokenizer-cache checks passed.
- Reasoning telemetry: 11 Nemotron calls, zero judge/hosted experiment calls, four agent SQL calls, 19.237 seconds within the 360-second reasoning budget. Import/measurement startup is separate from those agent SQL counts.
- Application fixes/retries: **none**. The auxiliary replay checker initially selected archived fixtures only; loading the live World Model resolved its missing-evidence lookup. Both validation attempts are retained in the audit.

[Validation summary and hashes](../logs/sample/live_upload_validation.jsonl). The report is retained locally in `logs/live_upload_report.json` and `logs/investigations/d81b88c5df6c4f2dbc10399db14283b9.json`; its complete supporting evidence closure is in `logs/live_upload_world_events.jsonl`. Normal service, measurement, World Model and checker JSONL logs remain in `logs/`. The uploaded content is not included in this status document.

This proves the bounded bundled-template path through the launcher, PostgreSQL ingestion, Zetaris reads, local measurements, Nemotron planning and deterministic checking. It does not validate arbitrary customer exports, Hindi/voice uploads, remote stacks, translation equivalence, model quality or production latency. Review status remains pending; quality is **verify on your sample**. Demo mode still replays saved synthetic companies and cannot run uploads.

Steps 0–6 were committed and pushed as `8768240` before this live attempt.
