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
