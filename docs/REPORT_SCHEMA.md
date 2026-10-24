# Investigation API and report schema (PROMPT-04)

Run `.venv/bin/polytoken serve` from the checkout. It serves the API on
`http://127.0.0.1:8000` and the registered reference URLs on
`http://127.0.0.1:55433/prices.json` and `/prices.schema.json`. A matching existing
reference server is reused. An empty legacy REST schema is refreshed using the
installed Zetaris metadata commands, preserving the registered URL. The source
PostgreSQL database and Zetaris must already be running as documented in README.
No UI is included.

## Routes

- `POST /investigations`: JSON `{company, question?, monthly_chats?, latency_target_s?}`.
  Company is `samudra` or `swara`; supplied volume and latency must be positive.
  Returns HTTP 202 with `{id}`. One worker serializes investigations to protect
  the shared SQLite state and provider limiter. Queued waiting is outside a run's
  budget. Budgets start after configuration and catalogue startup.
- `GET /investigations/{id}/events`: replayable SSE; supports `Last-Event-ID`.
  Each SSE frame has zero-based `id`, `event`, and JSON `data`. Keepalive comments
  have no event ID. An unknown run returns 404. Live SSE state is process-local.
- `GET /investigations/{id}/report`: report JSON, HTTP 202 while running, 404 for an
  unknown ID. Completed reports are also read from `logs/investigations/{id}.json`
  after a restart.
- `GET /evidence/{id}`: World Model event, including kind, payload, provenance,
  event ID, item key and sequence. Returns 404 if absent.
- `GET /companies`: live Zetaris configuration summaries; no direct fixture read.

The service binds to loopback. It is a local demonstration service, not a
multi-tenant or public deployment.

## Events

All events have `event`, ISO UTC `timestamp`, `investigation_id`, `step`, and
`why` (the validated planner explanation, at most forty words). Reasoning step order is
clarify, measure, locate, hypothesise, experiment, judge, speed, check, report.
The experiment step queues a job; judge and speed are deferred. After the first
checked report, the background worker executes experiment, judge and speed,
rechecks every claim, then emits experiment_done and done.
Partial runs may end before reaching all steps.

| Event | Additional fields |
| --- | --- |
| `step_started` | none |
| `tool_called` | `tool`, `args` (validated against that step's permitted choices) |
| `evidence_added` | `evidence_id`, `kind` |
| `finding` | `text`, `evidence_ids`; clarify can include `remembered` sources |
| `budget` | `nemotron`, `hosted`, `sql`, `duration_s`, `remaining_s`, nullable `reason` |
| `claim_dropped` | `id`, `reason` |
| `experiment_progress` | `done` (successful calls, including cache hits), `failed`, `total` (40); counts increase in completion order |
| `experiment_done` | `status`, `done` (complete pairs), `total` (20); emitted after final checker pass |
| `done` | `status`, `report_url` (startup failures may lack a URL) |

Within a normal step, `step_started` precedes `tool_called`, followed by evidence
and findings, then `budget`. Final evidence and checker rejection events may
follow the last step budget. `done` is always last. Events are written to
`logs/agent_events.jsonl`; CLI demo events are additionally appended to
`logs/sample/agent_<company>.jsonl`. Startup failures are logged and surfaced by
the API as a partial report. SSE reconnect replay lasts for the server lifetime.

## Report envelope

```json
{
  "schema_version": "2",
  "id": "run UUID",
  "company": "samudra",
  "status": "running | complete | partial",
  "partial_reason": null,
  "needs_input": [],
  "top_finding": "Evidence-based attribution, or null",
  "top_fix": "english_system | answer_cap | model_switch | null",
  "money_status": "quoted provider scenario; content only | money unavailable",
  "quoted_price": {"model": "...", "provider": "...", "source_url": "...", "fetched_at": "..."},
  "claims": [],
  "dropped_claims": [],
  "fixes": [],
  "quality_status": "automated pass; native review pending | failed or not fully judged",
  "review_status": "pending",
  "speed_status": "not measured | incomplete; insufficient valid runs | inconclusive | changed faster | changed slower",
  "remembered": [],
  "remembered_fields": [],
  "remembered_findings": [],
  "experiment": null,
  "markovian_runs": [],
  "limitations": [],
  "evidence_ids": []
}
```

A `running` report exposes `jobs.status` as queued or running, with the selected
lever and hosted model in `jobs.request`. The same report ID and persisted file are
updated when jobs finish. The API returns that JSON with HTTP 202 while running.
`jobs.budget` is the final sourced job telemetry; its numeric values also appear
as verified `jobs/*` claims.

A `complete` run completed the workflow; it does not imply that a fix passed.
A `partial` run gives the exact budget or unavailable-step reason. Missing
measurements are omitted, never replaced by zero. A missing verified price
produces `money unavailable`. Missing required configuration becomes `needs_input`
only after consulting bot_config and sourced company memory. User overrides have
explicit provenance. Repeated runs expose recalled profile IDs and fields.

Every report metric is in `claims`, never an unsupported display number:

```json
{
  "id": "baseline/<tokenizer>/monthly_inr",
  "text": "baseline <tokenizer> monthly_inr",
  "value": 123.45,
  "unit": "INR",
  "evidence_ids": ["evt_..."],
  "recompute": {"operation": "baseline", "inputs": {"snapshot": "evt_...", "prices": "evt_...", "fx": "evt_..."}},
  "verified": true
}
```

The number above is illustrative schema data, not a measured result. UI consumers
must look up claims by exact ID; do not infer zero from an absent ID. Tokenizer
IDs contain `/`, so do not parse with fixed-position splitting. Recompute
operations are a closed allowlist, not executable expressions. The checker
validates the World Model's content hashes and all transitive support events,
then recomputes from evidence payloads alone. Integers compare exactly, ratios
use relative tolerance 1e-9, and money permits at most INR 0.01 error. A tampered
source measurement drops all dependent claims. Dropped entries contain `id` and
`reason` but no renderable value.

## Claim IDs for the UI

- `baseline/<tokenizer>/monthly_inr`: historical whole-chat content bill, at the
  configured monthly volume and explicitly quoted provider's price. The source
  config names a model, not a provider; selecting the lowest input-price verified
  quote is a disclosed scenario, not the company's invoice.
- `baseline/<tokenizer>/{chat_count,requests,monthly_chats,billed_input,billed_output,billed_system_input}`.
- `baseline/<tokenizer>/<part>_{tokens,share,cost_share}` where part is
  `system_prompt`, `user`, `assistant` (prior-answer replay as input), or `output`.
  Shares use all billed content tokens or all priced billed content respectively.
- `ratios/<tokenizer>/<part>/{native_to_english_ratio,ci_low,ci_high,paired_items,cluster_count}`.
  Parts are `system_prompt`, `user`, `assistant`. Intervals use the pre-registered
  paired whole-chat bootstrap, not independent turn resampling.
- `baseline/<tokenizer>/english_system_monthly_saving_inr`: measured content-count
  substitution estimate. Experiment overhead and generated answers are separate.
- `baseline/<tokenizer>/half_answers_monthly_saving_inr`: **hypothesis**, assuming
  half the answer and replayed-answer tokens; it is not a measured fix result.
- `hypotheses/<alternate-tokenizer>/switch_monthly_saving_inr`: alternate measured
  tokenizer and published provider-price scenario; no output quality implied.
- `experiment/{original,changed}_{input_tokens,output_tokens,monthly_inr}` and
  `experiment/{completed_pairs,monthly_saving_inr,inr_per_rupee_input_mtok}`.
  Version 2 uses the same historical whole-chat billing reconstruction as the
  baseline. Prompt levers replace only the measured system tokens, including the
  reply-language instruction; historical replies and replay remain fixed. These
  deterministic scenarios do not depend on completed generation. Model switches
  use the alternative measured tokenizer and its published provider quote.
  Version 1 archived reports retain the former sampled-last-turn basis and
  are replayed with their original formula.
- `experiment/{original,changed}_output_tokens`, `experiment/output_tokens_change`
  and `experiment/output_tokens_ratio`: generated output length across twenty
  complete pairs, measured with the company tokenizer. This is separate from the
  historical cost scenario; no generated-output savings are inserted into it.
- `baseline/<tokenizer>/english_system_inr_per_rupee_input_mtok`: monthly input
  savings for every INR 1 per million input tokens. Rescaling does not assume a
  verified price or an output-token saving.
- `quality/{passed,judged,queued_for_review}`. Passing means at least eighteen
  same-facts verdicts across twenty judged pairs. Any incomplete judging prevents
  a pass. The judge is not invoked unless all twenty distinct pairs are complete;
  an incomplete sample has status `insufficient sample`, never pass or fail. Native review remains pending even after an automated pass.
- `speed/completed_runs`; `speed/<metric>/{original_median,original_min,original_max,changed_median,changed_min,changed_max,paired_difference,difference_min,difference_max}`.
  Metrics are `ttft_s`, `output_tokens_per_s`, `latency_s`. Difference is changed
  minus original; adjacent AB/BA runs form temporal pairs. Inconclusive means
  paired differences cover zero or total-latency spread covers the median effect.
  Throughput uses response usage; missing stream usage invalidates a speed row.
- `budget/{nemotron,hosted,sql,duration_s,remaining_s}`: reasoning-loop snapshot.
- `jobs/{nemotron,hosted,sql,duration_s,remaining_s}`: final investigation call
  counts and elapsed job time; call counts include reasoning and job attempts,
  while duration is only the job. Hosted retries count toward seventy.
- `markovian/<log-index>/{net_tokens,net_percent}`. Positive means savings;
  negative means extra tokens. The spec's clamped fields remain in raw telemetry
  only. All runs from `logs/agent_markovian.jsonl` at startup, plus this run, appear
  in the report; no best-run selection. Each has a measured/estimated token label.
  Reasoning planner usage contributes to chunk counts; version 2 deferred judge
  usage is outside the reasoning chunks and separately audited. In version 1,
  both planner and judge usage contributed to the chunks; hosted experiment calls are
  separate telemetry. The comparison is the reference counterfactual, not an
  independently measured naive run.

## Fixes and review

`fixes` are ranked by expected monthly saving and reference their checked
`claim_id`. Each has `lever`, `basis`, `status`; model switches also name the
candidate `tokenizer`. Status is `untested estimate`, `insufficient sample`, `rejected`, or
`provisional; native review pending`. Tested fixes include `reason`,
`model_label`, and `experiment_evidence_ids`. `top_fix` selects the first
provisional tested fix, not an untested or rejected hypothesis.

The budget permits one complete paired experiment per run. All other hypotheses
stay untested. A/B uses the same sampled last user turns and temperature zero.
Prompt levers hold the hosted model constant; model switching holds the system
prompt constant across different hosted families. The fixed seed selects distinct
chats. Native review queue rows retain both answers, the user turn, model names,
provenance and `pending` status in `logs/native_review.jsonl`.

Qwen 3 has no hosted family in the supplied catalogue. Its A/B and speed evidence
is labelled `tested on a stand-in model`. Token and money projections still use
its real tokenizer and quoted price. Even a same-family hosted Llama model is not
claimed to be the deployed model. Catalogue allowlists are intersected with a
live `/models` response and successful recorded serving probes before each
production run. `data/reference/nvidia_hosted.json` records each model’s
`serving_verified_at`, short/long results and source log. A listing alone never
makes a model eligible.

## Provenance and implementation references

Evidence payloads, failed rows, planner fallback records, native review queue,
budget, API events, generated usage and checker outcomes all go to `logs/` JSONL.
The runtime World Model and H-MEM persist under `.cache/state/`. The CLI appends
sample events and writes `agent_<company>_report.json`, retaining any old report
under its run ID instead of overwriting it silently.

FastAPI lifecycle and streaming follow the official
[lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/) and
[StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/)
documentation. The public [Zetaris SQL guide](https://kbase.zetaris.com/knowledge/sql-guide)
describes REST registration; the exact installed `DROP LIGHTNING DATABASE TABLE`
syntax was verified against the installed driver and the local service.

Planner and judge requests explicitly set `chat_template_kwargs.enable_thinking`
to false so the bounded output allowance is used for validated JSON rather than
an unfinished reasoning trace. This follows NVIDIA's documented
[direct-answer request option](https://build.nvidia.com/playbooks/nim-llm/instructions).
The first live run predates this correction and is retained in the event/report
archive. Paired generation uses at most four concurrent workers; every request
still uses the shared sliding-window limiter and per-investigation budget.

Failed HTTP responses have redacted status and detail in `logs/llm_errors.jsonl`.
Call rows distinguish a physical attempt from a budget rejection before dispatch.
Historical runs with unknown usage in failed Nemotron attempts are labelled
estimated when included in later reports. Original run logs remain unchanged.

The final BudgetGuard reserves two seconds of its six-minute wall allowance for
checking and serialization after external work stops. Earlier retained deadline
runs reported about seventy milliseconds of finalization after the call deadline;
their recorded durations are not rewritten. Startup catalogue discovery and REST
registration checks are logged separately from the agent's bounded SQL tools.


## Background job limits and replay (24 October 2026)

The API worker executes queued jobs after publishing the initial reasoning report;
CLI waits for the same job lifecycle before exiting. HTTP calls run in four
threads, and all World Model writes stay on the owner thread. The reasoning loop
has six minutes; its job has thirty minutes and shares the 25 Nemotron / 70 hosted
physical-attempt caps. Hosted reads have a 120-second timeout with at most two
retries, including HTTP transient failures; every attempt uses the same limiter.
Samudra hosted replies have a 200-token cap and Swara 600. Job quality judging uses
the one injected Nemotron generator and the remaining investigation call budget.

Successful raw generations are content-addressed World Model evidence. Cache keys
include model, system SHA-256, company/chat identity, user text, temperature and
reply-token limit. Completed calls are reused across reruns; failed calls are
retried. Cache hits retain original timing/provenance and are re-tokenized for the
current price scenario. Speed trials include the ABBA position in their cache identity, so reruns also
reuse successful speed trials with their original timestamps. Mixed cached/new
speed runs are reported as inconclusive because adjacent trials no longer share
the same measurement session. A process restart requires rerunning the investigation; successful
A/B calls resume from evidence, but in-flight work is not silently auto-resumed.

Use `polytoken investigate --company samudra --sample-suffix v2` (then Swara) to
write `agent_samudra_v2.jsonl` and `agent_samudra_v2_report.json` without replacing
previous samples. All raw attempts, cache hits and checker decisions remain in logs.

GPT-OSS may spend its reply-token budget on reasoning before emitting content.
The serving probe accepts `--model` and `--reasoning-effort` for an explicit
follow-up trial, preserving earlier observations. The verified model's
`generation_options.reasoning_effort` is sent unchanged by jobs and included in
cache identity and raw request metadata. This follows NVIDIA's documented
[GPT-OSS reasoning effort parameter](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b-infer).
The reply-token caps remain 200/600; an empty answer is a failed observation.
