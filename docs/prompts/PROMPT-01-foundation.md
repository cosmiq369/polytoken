# PROMPT-01: Foundation (config, LLM generator, Zetaris client, logs, doctor)

Model: Sol
Effort: high
Why: a focused, bounded build of core plumbing where correctness matters more than session length.

## Read first
- AGENTS.md (this repo) and docs/DECLARATIONS.md
- ../solve-it/README.md and ../solve-it/src/indictax/{tok,fertility,client,corpus,textstats}.py (read only; never edit or run git there)
- ~/zetaris-platform/README.md and ~/zetaris-platform/verify.sh (the login + SQL calls to copy)

## Branch
Create `feat/foundation` from the current tip of `main`. Commit small steps there. Push the branch. Do not merge, tag or release.

## Build
1. **Project**: `pyproject.toml` for package `polytoken` (Python 3.10+). Dependencies: httpx, python-dotenv, pytest (dev). Install `indictax` editable from `../solve-it` and document the two install commands in README.md. No agent frameworks.
2. **`polytoken/config.py`**: load `.env`; one typed settings object; a clear error naming any missing variable (never print values).
3. **`polytoken/logs.py`**: append-only JSONL writer to `logs/<stream>.jsonl` with `ts` (UTC ISO), `run_id`, `event`, and fields. Never write keys, tokens or passwords.
4. **`polytoken/llm.py`**: the ONE injected generator (the Meterless seam):
   `generate(prompt, system_prompt=None, attachments=None, on_stream=None, abort=None) -> {text, usage, latency_s, model}`
   - OpenAI-compatible chat completions at `NVIDIA_BASE_URL` with `AGENT_MODEL`.
   - Client-side rate limiter: token bucket at `NVIDIA_RPM` requests/minute (default 40), shared by all callers in the process.
   - Bounded retries with exponential backoff and jitter on 429 and 5xx (max 3), honour `Retry-After`. Timeouts on every call.
   - One JSONL row per call in `logs/llm_calls.jsonl`: model, prompt and completion token counts (from usage), latency, attempt, ok, error class. No prompt text, only its length and a short hash.
5. **`polytoken/zetaris.py`**: client for the local platform:
   - `login()` via `POST {ZETARIS_URL}/api/auth/login`; read the JWT and `orgId` from the response (orgId is not always 1).
   - `query(sql, page_limit=1000) -> list[dict]` via `POST /api/proxy/query/sql/start` with `Authorization`, `X-Org-ID`, `X-Request-ID` (uuid4). Re-login once on 401. Raise a clear error on any other failure with the first 200 characters of the body.
   - One JSONL row per query in `logs/zetaris_queries.jsonl`: sql (truncated to 500 chars), rows returned, latency, ok.
6. **`polytoken/tokens.py`**: thin wrapper over `indictax.tok.load_tokenizer` with an in-process cache: `count(spec, text) -> int` and `fragment_rate(spec, text) -> float` if indictax exposes what is needed; otherwise only `count` and note the gap.
7. **CLI `polytoken doctor`** (console script). PASS/FAIL lines like verify.sh, non-zero exit on any FAIL:
   - required .env variables present (names only)
   - Zetaris: login, then `select 7 as seven` returns 7
   - NVIDIA: one call with `max_tokens` 8, through the generator (so it is rate-limited and logged)
   - indictax importable and one tokenizer loads (`unsloth/gemma-3-4b-it`), counting a short Telugu sentence

## Tests (pytest, no network by default)
- Rate limiter: with a fake clock, 41 calls in one minute at 40 RPM make the 41st wait.
- Retries: a fake transport returning 429 then 200 succeeds after one retry; four 503s fail after 3 retries.
- Zetaris: orgId parsed from a login body where it is not 1; 401 triggers exactly one re-login.
- Logs: rows are valid JSON, carry run_id, and contain no value of any .env secret.
- Config: a missing variable names the variable in the error.
- Live tests marked `live` (skipped unless `-m live`): doctor's three checks.

## Do not
- Commit `.env`, print secrets, or add heavy dependencies.
- Edit or run git in ../solve-it or ~/zetaris-platform.
- Start any agent logic, UI or data loading. That is the next prompt.

## Stop point and report
Stop when the full suite is green and `polytoken doctor` passes against the live services. Report:
1. Files created, and the commits pushed on `feat/foundation` (hashes).
2. Exact test command and its output summary.
3. Full `polytoken doctor` output.
4. Anything you could not do, and every deviation from this prompt, with the reason.
