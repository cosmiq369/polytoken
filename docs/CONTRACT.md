# PolyToken pre-registration contract

Status: approved by Mohan Chelluru on 24 Oct 2026, 19:11 IST.

Written 24 Oct 2026, before any demo data or measurement exists. Results are judged against this file, not tuned to fit it. Changes after data exists are allowed only as a dated addendum below, never by editing the text above it.

## Questions PolyToken must answer for a team
1. How much more does our workload cost in Telugu or Hindi than the same content in English, per model? (ratio to English, paired by item, bootstrap interval over items)
2. Where do the extra tokens come from? (system prompt, user turns, answers, tool or context text)
3. How much slower is a reply, from time to first token and output speed?
4. Which fixes reduce cost or latency without failing the quality bar, ranked by monthly saving at the team's volume?

## Demo companies (fictional) and planted ground truth
| Company | Product | Planted property | Expected top finding | Expected top fix |
|---|---|---|---|---|
| A: Samudra Telecom | Telugu customer-support chat bot | Long system prompt written in Telugu, short answers | System prompt is the largest share of input tokens on byte-fallback tokenizers (Llama 3.2, Qwen3) | Keep the system prompt in English, replies stay in Telugu; second: a model with better Telugu coverage |
| B: Swara Care | Hindi voice assistant | Short system prompt, long spoken-style answers | Output tokens dominate cost and reply time | Cap answer length and ask for concise spoken style; second: a model with better Hindi coverage |

PolyToken passes the demo only if it reaches each expected top finding through its own investigation, with evidence, and does not reach it by reading this file.

## Models
Tokenizers from `../solve-it/configs/tokenizers.yaml` (the eight families measured on 18 Sep 2026). Live speed tests only on models hosted on the NVIDIA API catalogue that share one of those tokenizer families, plus the agent model itself.

## Quality bar for any fix
- Nemotron judge: the fixed answer conveys the same facts as the original on at least 90% of a 20-chat sample.
- Native spot check: Mohan reviews 10 Telugu pairs; a Hindi reviewer checks 10 Hindi pairs. Any "different meaning" verdict blocks the fix.
- A fix that fails the bar is shown as rejected, with the reason.

## Agent limits per investigation
- At most 25 model calls and 60 SQL queries.
- Hard stop at 6 minutes wall time; partial results are reported as partial.
- NVIDIA rate limit respected with headroom (no rolling 60-second window above the configured limit).

## Addenda
(none yet)
