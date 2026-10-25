# PolyToken: instructions for coding agents (Codex, Claude)

## What we are building
PolyToken is an agent that investigates why AI workloads in Indian languages (Telugu, Hindi) cost more and run slower than English, and recommends fixes backed by verified evidence.
Open Agent Hackathon 2026, Track 02 "The Agent That Can Explain Why". Hard deadline: 27 Oct 2026 23:45 UTC (28 Oct 05:15 IST).

## Judged requirements (do not drop any)
- Zetaris is the data layer. Chats, the price table, measurements and reference sentences are queried through Zetaris SQL.
- Meterless engines are reference architectures we implement ourselves:
  - World Model: every observation (token count, price, latency, quality score) stored with source, query, time window and fetched_at.
  - Markovian: the long investigation runs in compressed chunks; projected vs actual token savings are logged.
  - H-MEM: memory of company profiles and past investigations.
- NVIDIA Nemotron is the agent's brain, called through ONE injected generator function. Model name, base URL and rate limit come from .env, never hardcoded.
- Every audit, telemetry and provenance record goes to logs/ as JSONL. If it is not in logs/, judges cannot see it happened.
- A deterministic checker recomputes every number before it reaches a report. Claims without valid evidence are dropped, never shown.

## Pre-existing components (declared in docs/DECLARATIONS.md)
- The measurement harness `indictax` at ../solve-it (github.com/cosmiq369/indic-inference-tax, MIT). Install the pinned Git dependency in pyproject.toml and import it; the editable local install is an optional development override. Do not copy its code into this repo, and do not edit or run git in ../solve-it.
- Useful entry points: `indictax.tok.load_tokenizer(spec)`, `indictax.fertility.measure(tokenizer, items)`, `indictax.corpus.load_corpus(path)`, `indictax.client.ChatClient` (OpenAI-compatible streaming), `indictax.textstats`.
- Its conventions apply to every number we show: paired comparisons as ratios to English; never fabricate or fill in a measurement; a failed call is a row with ok=false.

## Local services
- Zetaris runs in Docker from ~/zetaris-platform. Web UI and REST on http://localhost:3000.
  - Login: POST /api/auth/login with {"username","password"} returns a JWT and an orgId. The orgId is not always 1; read it from the response.
  - Query: POST /api/proxy/query/sql/start with headers Authorization: Bearer <token>, X-Org-ID: <orgId>, X-Request-ID: <uuid> and body {"select": "<sql>", "pageLimit": N}.
  - Reference implementation: ~/zetaris-platform/verify.sh. Health check: ./verify.sh in that folder.
- NVIDIA API: OpenAI-compatible, base URL from NVIDIA_BASE_URL. The key allows 40 requests per minute: use a client-side rate limiter and bounded retries with backoff, and cap rounds and model calls per investigation.

## Rules
- Never commit secrets. Keys live only in .env (gitignored). Keep .env.example updated with variable names only. Never log keys, tokens or passwords.
- Keep dependencies few and mainstream. No agent frameworks; the agent loop is ours.
- Work on feature branches with small commits. No force-push to main. No tags or releases.
- Tests use pytest. Network tests are marked `live` and skipped by default. Run the full suite before reporting, and include exact commands and results.
- When a task is done, stop and report. Do not start the next task unasked.

## Setup from a clone
For setup and installation requests, read the canonical
[`skills/polytoken-setup/SKILL.md`](skills/polytoken-setup/SKILL.md).
Interview the user first and follow its demo/live boundaries. The identical Claude
copy lives at `.claude/skills/polytoken-setup/SKILL.md`.

## Bring-your-data requests
For conversation export conversion, English baseline review and upload guidance,
read the canonical [`skills/polytoken-add-data/SKILL.md`](skills/polytoken-add-data/SKILL.md).
Interview first, keep conversion scripts and user samples in the user's own folder
outside the repo, and never label machine translations reviewed. The identical
Claude copy lives at `.claude/skills/polytoken-add-data/SKILL.md`.
