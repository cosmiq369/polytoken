# Declarations for the Open Agent Hackathon 2026 submission

Build window: 22 Oct 2026 00:00 UTC to 27 Oct 2026 23:45 UTC. PolyToken's own code starts on 24 Oct 2026.

## Pre-existing components
| Component | Origin | Licence | How PolyToken uses it |
|---|---|---|---|
| `indictax` measurement harness | github.com/cosmiq369/indic-inference-tax, commit `0f61ec90ae49082d0fef7a21774e746fe17ed1cf`, by the same author, first commits Sept 2026 | MIT | Imported as a library for tokenizer loading, token counting and OpenAI-compatible streaming calls |
| Seed parallel corpus (18 prompts, en/hi/te and romanized/code-mixed) | Same repo, `data/prompts/` | CC BY 4.0 | Reference sentences for English-vs-Indic comparisons |
| Zetaris platform | Zetaris, hackathon distribution | Sponsor licence | Data layer |
| Meterless engines (World Model, H-MEM, Markovian) | github.com/Meterless/Meterless at 1742dec56a66e58eef9dda2d2b865823758ca8cd | Apache-2.0 | Python implementation from the specs, conformance checks ported to pytest; see docs/METERLESS.md |

Everything else in this repository was written during the build window, with AI coding assistance (Codex, Claude) as the rules allow.

## Vendored files (unchanged)

| Repository path | Origin | Licence | SHA-256 |
|---|---|---|---|
| `data/reference/seed_v0_corrected.jsonl` | Author's local `../solve-it/data/prompts/seed_v0_corrected.jsonl`; corrected corpus is not in the public pinned commit | CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ | `bc4166f22c9839462e0231aa919ad4287026bdc127d32d4f2eabd7b4a86e0292` |
| `configs/tokenizers.yaml` | `../solve-it/configs/tokenizers.yaml`, byte-identical to https://github.com/cosmiq369/indic-inference-tax/blob/0f61ec90ae49082d0fef7a21774e746fe17ed1cf/configs/tokenizers.yaml | MIT | `1678b1de0327de50adc481a7c3ba384be06dfb05a2d1ceefbace383620b08424` |

Original review metadata is preserved; vendoring is not translation approval.
