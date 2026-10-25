# PROMPT-04C: A quality experiment that can be trusted: full context, an A/A floor, untruncated replies

Model: Astra
Effort: high
Why: protocol changes plus live runs and judging; long, tool-heavy.

Runs in parallel with PROMPT-05 (UI). PROMPT-05 owns `web/**` and the static-file mount it adds to `api.py`; do not touch either. Add CORS for `http://localhost:*` to the API so the UI can call it.

## Read first
- logs/sample/agent_v2_completion_report.md and logs/sample/agent_v2_quality_diagnosis.md (your own every-pair review)
- docs/CONTRACT.md including addenda

## Branch
Continue on `feat/agent` from `d582ffa`. Push the branch only.

## Why 1/20 and 0/20 cannot be read as "the fix fails"
Your diagnosis shows the experiment measured the protocol, not the fix:
- Generation saw only the last user turn, so replies answered a different question than the real chat did.
- The judge saw neither the policy nor the conversation, quoted text that does not exist, and penalised corrections of unsupported baseline claims.
- 13 Swara baseline replies stopped at 600 tokens. gpt-oss-20b is a reasoning model, and its reasoning counts against `max_tokens`.
- There was no A/A control, so we do not know how often the same prompt run twice is judged "different". Without that floor no A/B score means anything. (The reviewer's spec in PROMPT-04 left this out; that is the prompt's fault, not yours.)

## Changes (contract text unchanged; add one dated addendum describing this protocol before any new run)
1. Generation uses the full conversation up to the last user turn, with `Reasoning: low` for gpt-oss, `max_tokens` 1024, and records `finish_reason`. A truncated reply is regenerated once; if still truncated, the pair is excluded and replaced by the next chat in the fixed-seed order, and the report counts exclusions.
2. A/A control for each company: the original system prompt run twice on the same 20 chats, judged exactly like A/B. Report A/A same-facts n/20 as the judge-plus-model floor next to the A/B result.
3. Judge, one pair per call: give it the company policy, the conversation and both replies; ask it to list the factual claims a customer is told in each reply (plans, amounts, steps, safety instructions) and mark each as present, missing, contradicted or added. Same facts = no missing, contradicted or added material claim. Store the claim lists as evidence. If this exceeds 25 Nemotron calls, raise the agent budget in the same addendum to 25 for reasoning plus 45 for judging, and say so.
4. The verdict against the contract bar (18 of 20) is still reported exactly as before. Add an interpretation line: when A/A is itself below 18/20, write "the bar cannot be met by this judge and stand-in model; result inconclusive", never "fix failed".
5. Every earlier run and score stays in the logs and in the report history.

## Re-run live
Samudra (lever: English system prompt) then Swara (lever: answer-length cap), with their A/A controls. Save as `agent_samudra_v3.jsonl` and `agent_swara_v3.jsonl` with reports. Then ask Mohan, in your report, to review 10 Telugu pairs; produce `logs/sample/native_review_samudra.md` listing 10 pairs (fixed seed) side by side with the judge's claim lists, and a column for his verdict.

## Tests
Judge prompt includes policy and history; truncation triggers regeneration and exclusion; A/A and A/B are judged by the same code; the inconclusive rule. Default suite and `-m live` green.

## Stop point and report
1. Commits and tests.
2. Per company: A/A n/20, A/B n/20, exclusions, verdict and interpretation line, claim-level summary (missing, contradicted, added counts), before and after rupees per month, speed result.
3. Deviations.
