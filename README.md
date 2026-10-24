# PolyToken

PolyToken investigates the cost and latency of AI workloads in Telugu and Hindi,
using English as the paired baseline. This foundation provides typed configuration,
an injectable NVIDIA generator, Zetaris SQL access, tokenizer helpers and JSONL
telemetry. The investigation loop and data loading belong to later work.

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

The default test run blocks network connections and skips the three `live` tests.
`-m live` explicitly selects the Zetaris, NVIDIA and tokenizer probes. Doctor prints
one environment check and those three probes, then exits non-zero on any failure.
Its NVIDIA probe caps output at eight tokens; a reasoning model can spend those
tokens on reasoning and return no visible text. Success means a valid API response.

Zetaris must already be running. The client follows the platform's `verify.sh`:
it reads `idToken` and `orgId` from login, queries through the SQL proxy, and reads
the returned `records` list. A 401 causes at most one re-login per query.
`page_limit` limits this result page; the foundation does not fetch further pages.

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

Every production generator shares one process-wide token bucket. It starts with
`NVIDIA_RPM` burst capacity (at least one permit) and refills at `NVIDIA_RPM / 60`
per second. Each retry also consumes a permit. One process cannot change RPM after
initialization. HTTP 429 and 5xx receive at most three retries with exponential
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
