# PROMPT-02 decisions (24 October 2026)

## Demo data and accounting, fixed before token measurements

All 100 fictional chats (223 turns per company) and both configurations remain
`review_status=pending`. Samudra's Telugu policy has 787 whitespace-delimited
words. The paired English text is for comparison, not a verified translation.
Reference sentences preserve the harness's original `review` value as JSON text.
Prices remain an empty list; neither token ratios nor these shares establish
money savings, response latency, or translation quality.

The planted-property check uses **one system prompt per chat**, all user turns
once, and all assistant turns once. For each company/tokenizer:
`S = system_prompt_native_tokens * distinct_chat_count`, `U = sum(user_native)`,
`A = sum(assistant_native)`. Samudra system share is `S/(S+U)`;
Swara output share is `A/(S+U+A)`. This is a transparent corpus accounting
convention, not a reconstruction of billed multi-turn requests (which may resend
history/system prompts and include template tokens). Each native/English part
ratio is the ratio of summed paired counts, not an average of per-item ratios.
Data will not be adjusted after seeing results.

## Zetaris discovery and registration

Discovery began 2026-10-24 13:58:03 UTC with the requested read-only driver `bin`
listing and `seed-org.sh`/`seed-org.sql`. The bundled web UI revealed management
SQL at `POST /api/proxy/sql-editor/sqls/run-query` with `{"sql": "..."}`;
workload SELECTs use `/api/proxy/query/sql/start`. Both use the login JWT,
response `orgId`, and a fresh `X-Request-ID`. No manual UI steps are required.

This installed connector defaults PostgreSQL to the exact `public` schema and
compares explicit schema names for equality. Omitting `schema`, `%`, `*`, and
comma-separated schemas did not discover the four schemas. Read-only inspection
of the installed `JDBCDataSourceMeta` implementation confirmed that behavior.
The older public SQL manual's all-schema behavior/alias syntax does not match
this build. Consequently, `sql/company_schema.sql` creates nine live projection
views in the **demo database's** public schema, named `schema__table`. One
`company_systems` datasource registers them. All four original schemas stay
intact; no data is copied and no Zetaris stack files/configuration are changed.
This is the sole schema-registration workaround.

The build supports REST JSON tables. A loopback-only static server serves only
`prices.json` and its schema at port 55433. `polytoken_reference.prices` is the
second source, accessed by the driver through `host.docker.internal`. Its empty
JSON array returns zero rows; no placeholder price is fabricated. After prices
are populated in a later task, refresh the REST table's inferred schema before
selecting price columns. `reference.prices` also has the declared typed schema
and is seeded with the same empty list, but is not a replacement for the REST
source. The federation query includes a scalar REST row count so the second
source participates without filtering out results when empty.

Registration is idempotent: create missing source/container, refresh the named
view metadata, create the missing REST table, and verify all row counts.
Credentials are read from `.env`, passed only to the local service, and redacted
from application audit logs. Discovery completed within the 45-minute cap;
its measured completion is recorded in `logs/data_setup.jsonl`.
