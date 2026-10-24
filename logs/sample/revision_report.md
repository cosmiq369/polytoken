# PROMPT-03A verification report — 24 Oct 2026

Branch: `feat/p02-fixes`, based on verified `origin/feat/data = f27d8fb`.

All measurements below are recomputed from archived Zetaris rows and matched against the federation output before rendering. All reviews are pending; no price, cost or reply-time result is claimed.

## Data v2

| Company | Chats | Turns | Distinct user turns | Distinct answers | Prompt words | Sentences / distinct |
| --- | --- | --- | --- | --- | --- | --- |
| samudra | 50 | 223 | 124 | 99 | 747 | 102 / 102 |
| swara | 50 | 223 | 124 | 99 | 37 | 6 / 6 |

No assistant answer repeats within a chat. Both companies retain the 3–6 turn schedule. Fixed seed: 20261024. V1 data and original samples remain byte-for-byte archived; archive_manifest.jsonl verifies their hashes.

## Vendored hashes

`data/reference/seed_v0_corrected.jsonl`: `bc4166f22c9839462e0231aa919ad4287026bdc127d32d4f2eabd7b4a86e0292` (CC BY 4.0).

`configs/tokenizers.yaml`: `1678b1de0327de50adc481a7c3ba384be06dfb05a2d1ceefbace383620b08424` (MIT).

Harness pinned to `cosmiq369/indic-inference-tax@0f61ec90ae49082d0fef7a21774e746fe17ed1cf`; five stored counts reproduced from the installed Git dependency in a fresh non-editable venv.

## V2 native-to-English ratios (ratio of sums)

Columns are system prompt, user turns, assistant answers. Ratios are content-token comparisons, not money.

### samudra

| Tokenizer | System | User | Assistant |
| --- | --- | --- | --- |
| HuggingFaceTB/SmolLM3-3B | 9.488203 | 6.849790 | 7.473658 |
| Qwen/Qwen3-4B | 8.032258 | 5.795749 | 6.251329 |
| krutrim-ai-labs/Krutrim-2-instruct | 2.458259 | 1.917903 | 2.051220 |
| microsoft/Phi-4-mini-instruct | 2.016438 | 1.470588 | 1.713228 |
| openai/gpt-oss-20b | 2.016438 | 1.470588 | 1.713228 |
| sarvamai/sarvam-1 | 1.191278 | 1.020561 | 1.023195 |
| unsloth/Llama-3.2-3B-Instruct | 9.488203 | 6.849790 | 7.473658 |
| unsloth/gemma-3-4b-it | 1.781961 | 1.409260 | 1.563394 |

### swara

| Tokenizer | System | User | Assistant |
| --- | --- | --- | --- |
| HuggingFaceTB/SmolLM3-3B | 2.265306 | 2.249901 | 2.530470 |
| Qwen/Qwen3-4B | 4.040816 | 3.891710 | 4.560687 |
| krutrim-ai-labs/Krutrim-2-instruct | 1.660000 | 1.414500 | 1.644863 |
| microsoft/Phi-4-mini-instruct | 1.265306 | 1.175327 | 1.334075 |
| openai/gpt-oss-20b | 1.265306 | 1.175327 | 1.334075 |
| sarvamai/sarvam-1 | 1.055556 | 1.016730 | 1.150419 |
| unsloth/Llama-3.2-3B-Instruct | 2.265306 | 2.249901 | 2.530470 |
| unsloth/gemma-3-4b-it | 0.980000 | 1.021235 | 1.165359 |

## Selected 95% chat-bootstrap intervals

2,000 whole-chat resamples, seed 20261024, paired native/English counts, linear percentile endpoints. The same configuration in every chat gives a degenerate system-prompt interval.

| Company | Tokenizer | Part | Ratio | 95% interval |
| --- | --- | --- | --- | --- |
| samudra | unsloth/Llama-3.2-3B-Instruct | assistant | 7.473658 | [7.212551, 7.738691] |
| samudra | unsloth/Llama-3.2-3B-Instruct | system_prompt | 9.488203 | [9.488203, 9.488203] |
| samudra | unsloth/Llama-3.2-3B-Instruct | user | 6.849790 | [6.749374, 6.954586] |
| swara | Qwen/Qwen3-4B | assistant | 4.560687 | [4.513956, 4.606981] |
| swara | Qwen/Qwen3-4B | system_prompt | 4.040816 | [4.040816, 4.040816] |
| swara | Qwen/Qwen3-4B | user | 3.891710 | [3.810605, 3.975099] |

## samudra: native token shares under both conventions

All entries are percentages. S = system share of input; O = output share of total. Billed counts replay history per completed reply; corpus counts system once per chat and every turn once.

| Tokenizer | v1 corpus S | v1 corpus O | v1 billed S | v1 billed O | v2 corpus S | v2 corpus O | v2 billed S | v2 billed O |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HuggingFaceTB/SmolLM3-3B | 98.4171 | 2.1445 | 98.1727 | 1.0920 | 97.5661 | 2.7547 | 97.6531 | 1.4117 |
| Qwen/Qwen3-4B | 98.4193 | 2.1522 | 98.1669 | 1.0959 | 97.5663 | 2.7384 | 97.6697 | 1.4035 |
| krutrim-ai-labs/Krutrim-2-instruct | 98.3604 | 2.2092 | 98.1063 | 1.1252 | 97.4504 | 2.8757 | 97.5710 | 1.4751 |
| microsoft/Phi-4-mini-instruct | 98.3009 | 2.3173 | 97.9829 | 1.1802 | 97.5265 | 2.9750 | 97.4991 | 1.5246 |
| openai/gpt-oss-20b | 98.3009 | 2.3173 | 97.9829 | 1.1802 | 97.5265 | 2.9750 | 97.4991 | 1.5246 |
| sarvamai/sarvam-1 | 98.1018 | 2.1645 | 97.8520 | 1.1022 | 97.2712 | 2.8383 | 97.3463 | 1.4550 |
| unsloth/Llama-3.2-3B-Instruct | 98.4171 | 2.1445 | 98.1727 | 1.0920 | 97.5661 | 2.7547 | 97.6531 | 1.4117 |
| unsloth/gemma-3-4b-it | 98.2731 | 2.2930 | 97.9989 | 1.1681 | 97.4636 | 2.9461 | 97.4122 | 1.5091 |

## swara: native token shares under both conventions

All entries are percentages. S = system share of input; O = output share of total. Billed counts replay history per completed reply; corpus counts system once per chat and every turn once.

| Tokenizer | v1 corpus S | v1 corpus O | v1 billed S | v1 billed O | v2 corpus S | v2 corpus O | v2 billed S | v2 billed O |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HuggingFaceTB/SmolLM3-3B | 63.4068 | 78.4732 | 30.2961 | 46.7996 | 49.4564 | 69.0521 | 32.8510 | 42.8090 |
| Qwen/Qwen3-4B | 63.5389 | 79.1553 | 29.6268 | 47.2090 | 50.2258 | 69.6001 | 32.8848 | 43.0874 |
| krutrim-ai-labs/Krutrim-2-instruct | 67.6998 | 77.5630 | 33.2551 | 46.1678 | 53.6176 | 67.8638 | 36.0363 | 41.7529 |
| microsoft/Phi-4-mini-instruct | 63.6550 | 78.2512 | 30.7407 | 46.7390 | 51.1298 | 68.5153 | 34.2083 | 42.3740 |
| openai/gpt-oss-20b | 63.6550 | 78.2512 | 30.7407 | 46.7390 | 51.1298 | 68.5153 | 34.2083 | 42.3740 |
| sarvamai/sarvam-1 | 63.8727 | 77.9774 | 31.1510 | 46.5855 | 51.5930 | 68.6279 | 34.5264 | 42.5074 |
| unsloth/Llama-3.2-3B-Instruct | 63.4068 | 78.4732 | 30.2961 | 46.7996 | 49.4564 | 69.0521 | 32.8510 | 42.8090 |
| unsloth/gemma-3-4b-it | 62.4204 | 79.7503 | 28.6313 | 47.7084 | 48.5437 | 69.6567 | 31.9902 | 43.3121 |

Full integer totals, English counterparts, all v1/v2 bootstrap intervals and source queries are in planted_properties.jsonl, bootstrap.jsonl and measurement_snapshot.jsonl (v1 recomputations in v1_recomputed/). Original v1 federation and shares remain in v1/.

## Validation

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q`: 99 passed, 6 skipped.

- `uv venv .cache/pin-check` then `UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .cache/pin-check/bin/python '.[dev]'`: installed pinned Git harness in a fresh venv; no editable sibling import.

- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .cache/pin-check/bin/python scripts/check_pin.py`: 99 passed, 6 skipped; all five stored counts matched. Pin provenance and exact results: pin_check.jsonl.

- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" .cache/pin-check/bin/python -m pytest -q -m live`: 6 passed, 99 deselected.

- `PYTHONDONTWRITEBYTECODE=1 .cache/pin-check/bin/python scripts/seed_company_db.py`: 50 chats / 223 turns per company, 118 reference variants, 0 prices; live test repeats seeding twice.

- `PYTHONDONTWRITEBYTECODE=1 .cache/pin-check/bin/python scripts/register_zetaris_sources.py`: existing SQL sources refreshed and counts verified.

- `PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" HF_HUB_OFFLINE=1 .cache/pin-check/bin/polytoken measure --company all`: 16 completed batches, 7,168 rows, 48 verified federation groups; none skipped or failed.

## Deviations and interpretation limits

- Existing v1 samples remain unchanged in v1/. Newly computed v1 billed shares and intervals are in v1_recomputed/ so preserving the old results does not overwrite them.

- Unanswered trailing user turns are excluded from billed requests. Counts exclude chat-template overhead and retries; published cache pricing is required before a discount is applied.

- The fixed-seed conversations still share topic templates. Cluster intervals describe these synthetic fixtures, not a representative population or translation quality.

- Tokenizer files were reused from the existing Hugging Face cache. The harness itself was fetched and installed from its public pinned Git commit, with no local editable dependency.

- The requested work_state tools were not exposed in this session. Progress and evidence were retained in logs/. Network-denied sandbox attempts were retried with approved access.

- Session B files, the agent loop, UI, prices, main, tags, and the sibling/platform repositories were not changed. A model setting cannot be changed by this chat; the prompt’s model/effort header was treated as execution guidance.

Changed files and commit hashes are recorded in validation.jsonl and the final completion message.

## Implementation commits

- `1a7c655` — fix: pin public indictax and vendor runtime reference data
- `275028a` — fix: preserve v1 and replace padded repetitive demo fixtures
- `bb6bdd5` — fix: reconstruct billed history and bootstrap paired chat clusters

The following evidence-only commit contains the completed report and samples. Full changed-file inventory: `validation.jsonl`.
