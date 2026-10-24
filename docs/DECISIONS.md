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

# PROMPT-03A decisions (24 October 2026)

The contract addenda were written before v2 remeasurement. The F4/F5 changes
repair realism defects found in review; the v1 results were not overwritten.
`data/demo/v1/` and `logs/sample/v1/` preserve every original file byte-for-byte;
`logs/sample/archive_manifest.jsonl` records their hashes. Additional v1 accounting
and chat-bootstrap results live separately in `logs/sample/v1_recomputed/`.
Both versions' raw measurement evidence was read through Zetaris and retained
in `measurement_snapshot.jsonl` for independent recomputation.

Billed accounting reconstructs only completed replies: an unanswered final user
turn is retained in corpus totals but does not create a billed request. Each
reply replays the system and all earlier content; earlier assistant replies
therefore become later input. Native and English counts are both retained.
These are content-token reconstructions, excluding templates, tool overhead,
retries and unpublished cache discounts, not provider usage measurements.
No price, cost, latency or quality result is inferred from token shares.
The v1 Llama reconstruction reproduces review: Samudra system share of billed
input is 98.172668%; Swara billed output share is 46.799648% (corpus 78.473230%).

The fixed seed is 20261024. V2 has the same 50 chats and 223 turns per company;
the 3/4/5/6-turn length schedule is unchanged. Samudra combines ten support
situations with five fictional plans, whose data, validity and message allowances
are embedded in the system prompt. Swara combines ten administrative/general
information topics with five access needs. No medical advice or plan prices
were added. Distinct wording is not proof of independent semantic samples: the
synthetic topic templates remain shared. Chat-cluster intervals characterize
these fixtures, not production traffic or translation quality. All review
statuses remain pending. The bootstrap samples 50 whole chats with replacement,
uses 2,000 replicates and linear 2.5/97.5 percentiles of the ratio of sums.
The system prompt contributes once per resampled chat, so its interval is
necessarily degenerate when every chat uses the same configuration.

The harness runtime is installed from the pinned public Git commit. The corrected
corpus is explicitly attributed to the author's local file, not falsely claimed
to exist at that public commit. Non-editable installations locate data relative
to the cloned repository working directory; run the documented commands there.
The optional editable development override is preserved. No code or repository
state in the harness or Zetaris platform was modified.

The session's requested claude-mem work_state tools were absent from the available
tool inventory; verification and progress evidence are recorded under logs/.
Sandbox network restrictions required escalated access for Git, package install
and local-service calls. Hugging Face tokenizer files were reused from cache
with HF_HUB_OFFLINE=1 for the pin recount and all eight measurement runs.
The fresh venv used its installed pinned harness, with no editable sibling import.
