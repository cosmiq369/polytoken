# Declarations for the Open Agent Hackathon 2026 submission

Build window: 22 Oct 2026 00:00 UTC to 27 Oct 2026 23:45 UTC. PolyToken's own code starts on 24 Oct 2026.

## Pre-existing components
| Component | Origin | Licence | How PolyToken uses it |
|---|---|---|---|
| `indictax` measurement harness | github.com/mohanchelluru369-tech/indic-inference-tax, by the same author, first commits Sept 2026 | MIT | Imported as a library for tokenizer loading, token counting and OpenAI-compatible streaming calls |
| Seed parallel corpus (18 prompts, en/hi/te and romanized/code-mixed) | Same repo, `data/prompts/` | CC BY 4.0 | Reference sentences for English-vs-Indic comparisons |
| Zetaris platform | Zetaris, hackathon distribution | Sponsor licence | Data layer |
| Meterless engine designs (World Model, Markovian, H-MEM) | Meterless, hackathon resources | Sponsor reference designs | Implemented from scratch in this repo |

Everything else in this repository was written during the build window, with AI coding assistance (Codex, Claude) as the rules allow.
