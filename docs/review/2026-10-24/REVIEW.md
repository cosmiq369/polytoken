# Independent review, 24 Oct 2026 (Claude, reviewer)

Codex wrote the code; this folder holds the reviewer's own checks. The scripts count tokens with the raw Hugging Face tokenizer files and do not import polytoken or indictax.

## PROMPT-02 (feat/data, f27d8fb)
- R1: all 48 native/English part ratios and all 16 planted shares reproduced exactly (`recompute_p02.py`).
- R2: 86 passed / 6 skipped on a clean Linux copy at f27d8fb.
- R3: sliding-window limiter, 400 saturated calls: at most 38 starts in any rolling 60 s window (provider limit 40).
- R4: no value from `.env` in any tracked file or in history.
- F3 accounting, F4 repeated answers, F5 padded prompt, F6 hidden ../solve-it data dependency: fixed in PROMPT-03A.

## PROMPT-03A (feat/p02-fixes, 893eb28) and PROMPT-03B (feat/meterless, 1eecb62)
- R5: trial merge of both branches is conflict-free; on the merge, with indictax installed from the pinned public commit, 135 passed / 6 skipped; no `solve-it` path in src/ or scripts/.
- R6: v2 ratios, shares under both conventions and the Samudra / Llama 3.2 answer interval [7.2126, 7.7387] reproduced exactly (`recompute_v2.py`, `v2_extra.py`).
- R7: v2 data: 124 distinct user turns and 99 distinct answers per company, no answer repeated within a chat, Samudra prompt 747 words with 102 distinct sentences out of 102.
- R8: World Model stable ids strip only U+0300 to U+036F (and zero-width characters), as the Meterless reference does; Telugu and Hindi pairs stay distinct.
- F7: the first live Markovian run (carryover 800 tokens, 3 chunks) cost 3,441 tokens against 2,082 for naive history, 65% more, but logged `tokensSaved: 0` because the spec clamps savings at zero; the report quoted only the later run after carryover was cut. Log the signed difference next to the spec field, and report every run.
- F8: Nemotron did not emit `[TASK_COMPLETE]`; the run ended at `maxChunks`. Completion must come from validated structured output, not from the model typing a marker.
- N1: answer openings are still templated (all 50 Swara chats open an answer with "Yes, let us first"; 37 Samudra answers open with "Your next step as"). Disclosed by Codex; acceptable for synthetic fixtures.

## Reference data staged here for PROMPT-04
- `prices.json`: 7 verified entries (schema-valid with `polytoken.prices.load_prices`), sources in each row.
- `fx.json`: 94.9432 INR per USD, FBIL reference rate as at 1 pm IST, 23 Oct 2026, from rbi.org.in.
- `nvidia_hosted.json`: text models on the NVIDIA catalogue per measured tokenizer family (85 models listed on 24 Oct 2026). Qwen 3, Sarvam-1 and Krutrim 2 have none, so their speed cannot be measured there.

Headline at v2 (Samudra on Llama 3.2): billed input per chat 21,200 tokens with the Telugu system prompt, 2,680 with the English one (-87.4%). At 100,000 chats a month and $0.05 per million input tokens, that saves about $92.60 a month (about Rs 8,790): large as a share, small in money, because the configured model is a 3B model.
