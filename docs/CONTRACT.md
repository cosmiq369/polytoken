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


### 24 Oct 2026 — billed-token accounting (PROMPT-03A, F3)

Written after the PROMPT-02 measurements and before any price or cost exists.
Money uses billed content tokens of a stateless chat API: for reply k, input is
the system prompt plus every earlier user and assistant turn plus user turn k;
output is reply k. An unanswered final user turn has no completed request and is
excluded from billed input. The corpus convention remains reported for transparency.
Provider chat-template overhead and actual usage must be measured before claiming
an invoice-equivalent total; these content counts exclude that overhead.
Cached-prefix pricing is used only where a provider publishes a cache price.
The expected findings are unchanged and are judged on cost and reply time, not
on token share.

### 24 Oct 2026 — demo v2 and chat-level uncertainty (PROMPT-03A, F4/F5)

Review found repeated assistant answers, including repeats within a chat (F4),
and a repeated three-sentence suffix in Samudra's system prompt (F5). The v2
revision fixes realism defects, not measured results. V1 data and existing results
are retained byte-for-byte in data/demo/v1/ and logs/sample/v1/; both versions'
results will be reported. V2 uses a fixed seed, distinct conversations and a
non-repeating Telugu policy with fictional support knowledge. All reviews remain
pending. Native/English per-part ratios use 2,000 paired bootstrap resamples of
whole chats, with a fixed seed and 95% percentile intervals; each resampled chat
contributes its system prompt once. Repeated turns are not independent samples.
The tokenizer configuration and corrected reference corpus are now vendored with
hashes in data/reference/SOURCES.md; the eight tokenizer families are unchanged.

### 24 Oct 2026 — separate call budgets and controlled hosted experiments (PROMPT-04)

Written before any PROMPT-04 investigation run. The 25-call limit covers the
agent's own Nemotron calls, including planning, repair and quality judging.
Hosted fix experiments and speed probes have a separate limit of 70 calls per
investigation. Every physical attempt, including retries, counts; all calls use
one shared rate limiter. The SQL limit remains 60 and wall time six minutes.
A prompt fix is tested A/B on the same hosted model, with the same user turns
at temperature 0, comparing the original system prompt with the changed prompt.
Model switching is explicitly a different experiment with the prompt held fixed.
Stand-in hosted models are labelled, and cannot establish quality or speed on
the company's deployed model. Native review remains pending until human review.

### 24 Oct 2026 — background hosted jobs (PROMPT-04B)

Written before the PROMPT-04B serving probes and new company investigations.
The six-minute limit covers the agent's reasoning loop. Fix experiments and speed
probes are background jobs with a separate thirty-minute wall allowance and a
combined seventy physical hosted attempts per investigation, including retries.
Jobs use concurrency four, the shared NVIDIA limiter, a 120-second read timeout,
and at most two retries on timeout. Reply limits are 200 tokens for Samudra and
600 for Swara. The existing 25 Nemotron and 60 SQL call limits remain; deferred
quality judging shares the Nemotron call limit and the job deadline. Reports show
running jobs and are rechecked when results arrive. Only twenty complete pairs
permit quality judging; smaller samples are insufficient, never pass or fail.
Prompt-lever money reconstructs the same historical bill as the baseline with
measured changed-system tokens. Generated output-length changes are reported
separately. Served models must pass recorded probes; catalogue listing alone is
insufficient. Successful generation evidence is reused by model, system hash and
chat identity (with user text and generation settings included to avoid stale hits).
The quality threshold, human review requirement and expected findings are unchanged.
