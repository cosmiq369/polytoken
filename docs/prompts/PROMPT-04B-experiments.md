# PROMPT-04B: Make the fix experiments finish: hosted-model probe, background experiment jobs, re-run both companies

Model: Astra
Effort: high
Why: live diagnosis against the NVIDIA API plus code changes and two long live runs.

## Read first
- logs/sample/agent_completion_report.md, docs/REPORT_SCHEMA.md, docs/CONTRACT.md (addenda)
- logs/sample/agent_audit_llm_calls.jsonl and agent_hosted_diagnostics.jsonl

## Branch
Continue on `feat/agent` from `5e7e5ca`. Small commits, push the branch only.

## What the reviewer found in the PROMPT-04 logs
Nemotron is fine (32 of 33 calls ok, median 1.1 s). The experiments failed for two concrete reasons:
- `meta/llama-3.2-11b-vision-instruct`: 58 ReadTimeouts and 9 successes; successful calls took a median 28 s and up to 74 s with the long Telugu system prompt, while each call's timeout was clipped to about 35 s by the 6-minute deadline.
- `google/gemma-3-4b-it`: all 24 calls returned HTTP 404 within 0.3 s, although the model is listed in `/v1/models`. Listed is not the same as served.
- `openai/gpt-oss-20b` worked (30 ok, median 11.6 s).
So 0 of 20 pairs could be judged. The design, not the code, is the main cause: forty slow hosted calls cannot fit inside a 6-minute reasoning loop on the free tier.

## Step 0: probe what is actually served
For each of `meta/llama-3.2-11b-vision-instruct`, `meta/llama-3.2-90b-vision-instruct`, `google/gemma-3-4b-it`, `google/gemma-3-12b-it`, `openai/gpt-oss-20b`: a 3-try streamed probe with a short prompt, then 3 tries with Samudra's full Telugu system prompt and one chat. Record status, time to first token, total time and usage in `logs/sample/hosted_probe.jsonl`. For any 404, also try without a system message (some hosted models reject the system role) and record that. Add `serving_verified_at` and the probe result per model to `data/reference/nvidia_hosted.json`; a model that never answers is not used.

## Step 1: experiments as background jobs
1. Contract addendum, dated 24 Oct 2026, before any new live run: the 6-minute limit covers the agent's reasoning loop. Fix experiments and speed probes run as background jobs the agent starts, with their own caps (70 hosted calls and 30 minutes per investigation). The report shows them as running until they finish, and the checker re-verifies every claim when they do.
2. Job runner: concurrency 4 through the shared limiter, read timeout 120 s per call, up to 2 retries on timeout (each retry counts toward the cap), `max_tokens` 200 for Samudra replies and 600 for Swara. Results are cached as evidence, keyed by model, system-prompt hash and chat id, so a rerun never repeats a finished call.
3. New events: `experiment_progress {done, failed, total}` and `experiment_done`; the report updates in place. Add both to docs/REPORT_SCHEMA.md.
4. The judge runs only with 20 complete pairs; fewer gives "insufficient sample", never a pass or a fail.
5. After-fix money for prompt levers uses the same billed reconstruction as the baseline, with the changed system prompt's measured tokens (deterministic, no generation needed). Generated replies are for quality and output length only; report any output-length change separately.
6. Model-switch lever: use whichever other-family model passed Step 0 (gpt-oss-20b if Gemma is not served), and say which.

## Step 2: re-run live
Run `polytoken investigate --company samudra`, wait for its jobs to finish, then Swara. Keep earlier runs in the logs; add the new ones as `agent_samudra_v2.jsonl` and `agent_swara_v2.jsonl` with their reports. Do not open docs/CONTRACT.md to adjust anything.

## Tests
- Job runner with fakes: timeouts and retries count toward the cap; the cache skips finished calls on rerun; the judge refuses fewer than 20 pairs; progress events arrive in order.
- Default suite and `-m live` green.

## Stop point and report
1. Commits and test summaries.
2. The probe table (model, status, short-prompt and long-prompt time to first token).
3. For each company: reasoning-loop duration, job duration, call counts, top finding and top fix as the agent stated them, rupees per month before and after, quality n of 20 with judge verdict, speed medians and spread (or inconclusive), dropped claims, signed Markovian savings.
4. Every deviation, with the reason.
