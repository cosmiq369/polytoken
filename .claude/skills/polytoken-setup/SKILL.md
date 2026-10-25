---
name: polytoken-setup
description: Set up a cloned PolyToken checkout for offline replay or local Zetaris-backed investigations, diagnose dependencies, and explain unverified remote options.
---

# Set up PolyToken with the user

Work only in the chosen PolyToken checkout. Read its AGENTS.md. Never modify another
project, provision paid resources, or put credentials in chat, command arguments,
logs, screenshots or commits. Keep the canonical skill and `.claude/skills` copy identical.

## Interview before acting

Ask together, then tailor the path: OS; Python version; Docker installed/running;
Zetaris location (local Docker, existing installation, remote Docker host over SSH,
or skip for demo); NVIDIA key available; and which companies / anonymised or
synthetic data they want to investigate. A demo needs neither Docker nor keys.
Clarify that paired English translations are required for language ratios.

Before each step show its dry run (the intended command and affected paths, without
secrets). Reuse an existing healthy installation. Ask before **network installs**
and **every action on a remote host** unless the user already explicitly authorised
that exact step. Prefer local/offline verification while awaiting approval. Stop
that step after a failed attempt, diagnose, and give a concrete fix; do not reset
volumes, replace data or retry destructive commands.

## Demo path (fully offline after dependencies are installed)

Run from the clone root. `polytoken` resolves the checkout's web and reference files;
do not start it from an unrelated directory.

1. Dry run: `python3 --version`, inspect `.venv` without changing it. Require Python
   >=3.10. If absent, propose the OS-appropriate Python install and ask before doing
   a network install. Create a venv only if absent: `python3 -m venv .venv` (or
   `uv venv .venv`). Use that interpreter explicitly for every subsequent command.
2. Dry run: inspect `pyproject.toml` and the installed `indictax` direct URL metadata.
   After approval, `.venv/bin/python -m pip install '.[dev]'` (or
   `uv pip install --python .venv/bin/python '.[dev]'`). This installs the public
   `indictax` harness pinned to `0f61ec90ae49082d0fef7a21774e746fe17ed1cf`.
   **Meterless is not a pip dependency:** our engines implement the reference
   architecture at `1742dec56a66e58eef9dda2d2b865823758ca8cd`, documented in
   `docs/METERLESS.md`. Do not invent a Meterless install command. An installed
   harness with the same Git commit can be reused; do not substitute `../solve-it`.
   An offline cache may be used with `uv pip install --offline`; report a cache miss,
   then ask before retrying online. Never silently download tokenizers.
3. Dry run: check only whether `.env` exists, never display it. Demo works with no
   `.env`. For live mode create it from `.env.example` **only if absent**. Ask the
   user to enter secrets directly into the file using their editor, never into chat.
   Do not generate or guess provider credentials. `.env.example` has names only.
4. Dry run: explain that doctor creates a temporary SQLite probe under `.cache/state`
   and appends redacted results to `logs/doctor.jsonl`. Run
   `.venv/bin/polytoken doctor`. Missing keys and unprobed services are WARN in demo.
   Doctor checks Python, the actual pinned harness, local Meterless imports, writable
   SQLite, price freshness, free app port and disk. Its thirty-day quote-age policy
   is a setup warning threshold, not a claim that prices remain commercially valid.
5. Dry run: tests use temporary fixtures and skip network tests by default.
   `.venv/bin/python -m pytest -q`. Existing Node/Playwright can run UI checks; if
   unavailable, report skips and ask before installing browser tooling.
6. Dry run: check port availability using `doctor --port 8000`; reuse an already
   running matching instance rather than launching duplicates. Start
   `.venv/bin/polytoken serve --demo --port 8000` and open `http://127.0.0.1:8000`.
   Select New investigation → bundled sample → Run. It must say “Replay of a saved
   run”. Uploads must say “Live mode needed”. Saved numbers retain their original
   company, volume and candidate models. No key means no new agent run.

On Windows use `.venv\Scripts\python.exe` / `polytoken.exe`. This command spelling is
provided for convenience; the validated setup evidence is macOS, not Windows.

## Live local path (integration still requires verification)

First complete the environment steps above. Preserve any user datasets. The bundled
source seeder **replaces the four fictional datasets**; only seed a fresh demo source
or obtain explicit approval to refresh an existing demo database. Uploaded companies
use isolated generated schemas, and are not overwritten by the bundled seeder.

The verified route comes from the sponsor distribution's `README.md`,
`docker-compose.yml`, `preflight.sh` and `verify.sh` (the author's installation is
`~/zetaris-platform`). Read the user's copy before choosing commands; do not edit
that external checkout. PolyToken does not distribute Zetaris images, licences or
registry credentials. Obtain the sponsor download and registry access from the
Zetaris hackathon/cloud download portal; if unavailable, use demo mode. The supplied
stack uses private `zetarishackathon.azurecr.io` images, Docker Compose, and a separate
metadata PostgreSQL. Its README calls for at least 8 GB Docker memory and 4 CPUs.

For a local installation, show these as separate dry runs and ask before pulls:

- In the sponsor directory: `./preflight.sh`, then (approved) `docker compose pull`,
  `docker compose up -d`, `./verify.sh`. Reuse healthy services. Have the user sign in
  to the registry themselves; never copy the credential-bearing login command.
- Back in PolyToken, after the user fills `.env` locally:
  `docker compose --env-file .env -f infra/docker-compose.yml config --quiet` is the
  dry run (never print expanded compose configuration). Then
  `docker compose --env-file .env -f infra/docker-compose.yml up -d --wait` after
  approval if an image pull is needed. This app-owned PostgreSQL listens on local
  port 55432; it is distinct from Zetaris's metastore.
- Inspect the intended target and show the table names before
  `.venv/bin/python scripts/seed_company_db.py`. It creates schemas and seeds paired
  chats, reference sentences and prices; requires the approval described above for
  an already populated database. It never modifies the external Zetaris checkout.
- Start `.venv/bin/python scripts/serve_reference.py` once on local port 55433.
  `.venv/bin/python scripts/register_zetaris_sources.py` registers app projections
  and the REST price source. Registration is idempotent and should retain existing
  source credentials; resolve mismatches explicitly rather than replacing sources.
- Explain the tokenizer allowlist in `configs/tokenizers.yaml`; ask before the first
  `.venv/bin/polytoken measure --company all`, which may download tokenizer files.
  It queries chats through Zetaris and writes actual counts/batch failures to the
  app database. An unavailable tokenizer is missing data, never a zero count.
- `.venv/bin/polytoken doctor --live` probes the configured Zetaris TCP port, login,
  SQL result, populated views, live/reference price agreement and an eight-token
  NVIDIA completion using the production generator. It never prints secrets.
  A passing probe does not validate a complete investigation or a new model's quality.
- Run `.venv/bin/python -m pytest -q`, then start `.venv/bin/polytoken serve`.
  The launcher validates local JSONL/CSV; see `docs/SAMPLE_SCHEMA.md`. New samples
  are registered and measured through Zetaris before the bounded agent runs. All
  candidate tokenizers must already be cached; the launcher does not download them.
  Live reasoning sends workload summaries to NVIDIA. Remote Zetaris would receive
  imported conversation data. Do not promise that a remote deployment is local-only.

The source writer currently expects PostgreSQL at `127.0.0.1:55432`. Registration
expects Docker Desktop's `host.docker.internal`; Linux routing may need an explicitly
reviewed host-gateway mapping in the user's sponsor setup. Never silently alter it.
Use the returned Zetaris orgId; never assume the organisation is one. Keep the
reference server alive while SQL reads prices. Never expose a database port publicly.

## Remote Docker over SSH — Roadmap / unverified

No remote host or paid cloud resource has been created or tested for this skill.
The sponsor README documents Docker Compose on a server and HTTPS via Caddy, but
that alone does not validate PolyToken's source/REST connectivity. Do not claim
end-to-end remote support. After obtaining the hostname and explicit permission,
the first proposed step can be read-only `ssh HOST 'docker compose version'` and
reading that host's installed sponsor documentation. Even this action requires
permission. Have the user retain SSH credentials and host-key verification.

Before proposing a start or tunnel, resolve private routing from the Zetaris
containers to app ports 55432/55433, the REST endpoint, the JDBC registration URL,
and HTTPS requirements. A local SSH forward for the UI alone does not solve those
routes. Keep tunnel/remote-start commands under Roadmap until tested on the supplied
host; ask before every remote action. Never disable host-key checks, open public
DB ports, invent Terraform, or create cloud resources.

## Completion

Record commands, PASS/WARN/FAIL, skips and unverified paths in a completion note,
with audit evidence under `logs/`. Do not include any secret values. Report whether
only demo works, whether service probes passed, and whether an actual uploaded-data
investigation was verified. Stop after the requested setup; do not launch subsequent
experiments or video production unasked.
