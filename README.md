# PolyToken

PolyToken investigates the cost and latency of AI workloads in Telugu and Hindi,
using English as the paired baseline. This foundation provides typed configuration,
an injectable NVIDIA generator, Zetaris SQL access, tokenizer helpers and JSONL
telemetry. It also seeds fictional company data and measures paired token counts
through Zetaris. The investigation loop belongs to later work.

## Install

Use Python 3.10+ and `uv`. From the PolyToken directory, create and activate a
virtual environment, and keep Python bytecode inside this repository:

```sh
uv venv .venv
source .venv/bin/activate
export PYTHONPYCACHEPREFIX="$PWD/.cache/pycache"
export HF_HOME="$PWD/.cache/huggingface"
```

Run the two install commands:

```sh
uv pip install -e '.[dev]'
sh scripts/install-indictax.sh
```

The second command runs `uv pip install --editable ../solve-it`. It redirects
setuptools metadata and build output to PolyToken's `.cache/indictax/`, keeping
the reference repository read-only. No harness source is copied into PolyToken.

Copy `.env.example` to `.env` and fill in the required variables. Keep credentials
in `.env`, which is gitignored. Model names, endpoints and request limits come
from that environment file.

Required variables are `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `AGENT_MODEL`,
`ZETARIS_URL`, `ZETARIS_USER` and `ZETARIS_PASSWORD`. `NVIDIA_RPM` defaults
to 40 when unset or empty. `HF_TOKEN` is optional for the ungated doctor tokenizer.
Use the NVIDIA account's model catalog to choose an accessible Nemotron chat model;
a model appearing in the catalog does not guarantee that account can invoke it.

## Verify

```sh
python -m pytest -q
python -m pytest -q -m live
polytoken doctor
```

The default test run blocks network connections and skips all `live` tests.
`-m live` explicitly selects the Zetaris, NVIDIA and tokenizer probes. Doctor prints
one environment check and those three probes, then exits non-zero on any failure.
Its NVIDIA probe caps output at eight tokens; a reasoning model can spend those
tokens on reasoning and return no visible text. Success means a valid API response.

Zetaris must already be running. The client follows the platform's `verify.sh`:
it reads `idToken` and `orgId` from login, queries through the SQL proxy, and reads
the returned `records` list. A 401 causes at most one re-login per query.
`page_limit` limits this result page. A full page or metadata indicating more rows raises
`ZetarisTruncated`; `allow_truncated=True` explicitly accepts a partial result.
Every query logs `possibly_truncated`. No pagination route is assumed.

## Generator and telemetry

```python
from polytoken.config import load_settings
from polytoken.llm import NvidiaGenerator
from polytoken.logs import JsonlLogger

settings = load_settings()
logger = JsonlLogger(secrets=settings.secrets)
with NvidiaGenerator(settings, logger=logger) as generator:
    generate = generator.generate  # the single callable to inject into later engines
    result = generate("Reply with OK.")
```

`generate(prompt, system_prompt=None, attachments=None, on_stream=None, abort=None)`
returns `text`, provider `usage`, total `latency_s` and the configured `model`.
Missing usage remains missing. Attachments are OpenAI-compatible message content
parts. A callback enables SSE streaming. Cancellation accepts a `threading.Event`
or predicate and is checked before requests, during waits and between stream chunks;
an in-flight blocking read is bounded by its timeout.

Every production generator shares one process-wide sliding-window limiter. At most
`NVIDIA_RPM - 2` calls may start in any rolling 60-second window (38 by default).
RPM must be an integer of at least 3. Each retry also consumes a slot. One process
cannot change RPM after initialization. HTTP 429 and 5xx receive at most three retries with exponential
backoff, jitter and `Retry-After` support; other failures are raised immediately.
The default request timeout is 60 seconds, with a ten-second connect timeout.

Append-only records go to `logs/llm_calls.jsonl`, `logs/zetaris_queries.jsonl` and
`logs/doctor.jsonl`. Each HTTP completion attempt has its own row, including failed
attempts. A query has one row covering login and any re-login. Shared loggers keep
the same `run_id` across clients. Prompt and system text, attachments and responses
are excluded from LLM telemetry; only lengths, a short SHA-256 prompt hash, usage
counts and request metadata are recorded. Secrets are redacted recursively,
including .env/process secrets and login tokens returned by Zetaris.

`polytoken.tokens.count(spec, text)` and `fragment_rate(spec, text)` reuse cached
`indictax` adapters. Fragment rate is the share of encoded tokens whose
`is_fragment` flag is true, with zero for empty input, matching the harness.
All reference code stays in `../solve-it` and `~/zetaris-platform`; see
[the declarations](docs/DECLARATIONS.md) for provenance and licences.

## Demo company data and measurements (PROMPT-02)

Add `COMPANY_DB_USER` and `COMPANY_DB_PASSWORD` to `.env`. Use a new password for
this isolated fictional database. From PolyToken, with its virtualenv active:

```sh
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
PYTHONDONTWRITEBYTECODE=1 python scripts/seed_company_db.py
```

The seeder upserts checked-in JSONL for 50 chats / 223 turns per company, two bot
configurations, and 118 parallel reference variants imported from the declared
harness. Running it twice keeps the same counts. All generated rows remain
`pending`; no translation has been approved. The reference `review` field retains
its original JSON value. `scripts/generate_demo_data.py` reproduces the fixtures;
do not tune or regenerate them in response to measurement results.

Start the tiny price server in a separate terminal and leave it running:

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/serve_reference.py
```

Then register and measure:

```sh
PYTHONDONTWRITEBYTECODE=1 python scripts/register_zetaris_sources.py
PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" polytoken measure --company all
```

`--company samudra` or `--company swara` measures just that company. `all` also
runs and independently verifies the federation SQL. Every configured tokenizer is
attempted; load failures are explicit skipped batches with reasons and no count
rows. A failed batch is discarded in full. Direct PostgreSQL access is limited to
schema creation, seeding and measurement writes. All workload reads, reference
reads and the final proof use Zetaris SQL.

### Exact registration procedure

No manual UI operation is needed. The script logs in with `POST /api/auth/login`,
uses the returned JWT and `orgId`, and supplies `Authorization: Bearer …`,
`X-Org-ID` and a fresh `X-Request-ID` UUID. Management statements go to
`POST /api/proxy/sql-editor/sqls/run-query` as `{"sql": "<statement>"}`.
After `SHOW DATASOURCES`, create `company_systems` if absent (the placeholders
below are injected from `.env`, never written into documentation or logs):

```sql
CREATE DATASOURCE company_systems OPTIONS (
 jdbcdriver "org.postgresql.Driver",
 jdbcurl "jdbc:postgresql://host.docker.internal:55432/company_systems",
 username "<COMPANY_DB_USER>", password "<COMPANY_DB_PASSWORD>",
 schema "public", fetchsize "1000"
)
```

Refresh this explicit view list on every run:

```sql
REGISTER DATASOURCE TABLES (
 "samudra__bot_config", "samudra__chats", "swara__bot_config", "swara__chats",
 "reference__sentences", "reference__prices", "measurements__batches",
 "measurements__token_counts", "measurements__latest_token_counts"
) FROM company_systems
```

The views project all four schemas without copying data, working around the
installed connector's single-schema restriction. After `SHOW LIGHTNING DATABASES`,
create the following container if absent, and create the REST table only if a
SELECT reports that it does not exist:

```sql
CREATE LIGHTNING DATABASE polytoken_reference OPTIONS ()
CREATE LIGHTNING REST TABLE prices FROM polytoken_reference
 REQUEST(endpoint "http://host.docker.internal:55433/prices.json", method "GET",
 http_encoding "URLENCODED", response_type "JSON") HEADER() BODY()
```

Verify each registered table with `SELECT COUNT(*) AS n FROM company_systems.<view>`
and `SELECT COUNT(*) AS n FROM polytoken_reference.prices` through
`POST /api/proxy/query/sql/start`, body `{"select": "<SQL>", "pageLimit": 1000}`.
The script is safe to rerun; it does not drop sources or modify the Zetaris stack.

### Evidence and limits

`sql/token_ratio_by_part.sql` joins the chats/configurations, latest completed
measurement batches, grouped reference sentences, and the REST price row count.
Reference rows are grouped before joining to avoid multiplying token counts.
The checker independently sums every expected native/English pair and rejects
missing pairs, duplicate rows, or mismatched SQL aggregates before saving output.
The latest attempt supersedes older measurements even when skipped or failed.

Evidence goes to `logs/measurements.jsonl`, `logs/data_setup.jsonl`,
`logs/zetaris_admin.jsonl`, `logs/zetaris_queries.jsonl`, `logs/reference_http.jsonl`,
and verified samples in `logs/sample/federation.jsonl` and
`logs/sample/planted_properties.jsonl`. Database records include source queries,
fetched times, observation windows, tokenizer specs and run IDs.

`data/reference/prices.json` is deliberately empty. Its schema and loader reject
invalid prices, and `cost_usd` refuses unverified entries or missing input/output
prices. **Money is unavailable.** The zero REST row count is source coverage, not
a zero price. Populating the REST list later requires refreshing its inferred
schema before selecting price columns.

The token-share check counts one system prompt per chat and each recorded turn
once: system input share = `S/(S+U)`; output share = `A/(S+U+A)`.
It excludes replayed history, chat templates, retries and provider billing rules.
Token shares alone do not prove cost or latency dominance. See
[decisions and deviations](docs/DECISIONS.md) for the assumptions fixed before
measurement. All quality judgments remain pending native review.

After seeding, registration, and `measure --company all`, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 HF_HOME="$PWD/.cache/huggingface" python -m pytest -q -m live
```

The live suite also checks the idempotent PostgreSQL seeder, both company schemas,
and the independently checked federation. It requires the demo DB, Zetaris,
price server and completed measurements, in addition to the foundation services.
