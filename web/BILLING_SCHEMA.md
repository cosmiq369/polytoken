# Billing console API and recomputation

These display routes extend `docs/REPORT_SCHEMA.md`. The agent, tools, report
files and `Checker` implementation are unchanged. Legacy reports retain INR
claims; the new billing projection exposes canonical USD amounts.

## GET /currencies

Returns `{base: "USD", rates: [...]}`. USD is the identity denomination with rate
one and no fabricated FX source or date. Other rows contain `currency`, `per_usd`,
`source`, `source_url`, `as_of`, `fetched_at`, `verified`. The configuration is
`data/reference/fx.json`, with the same structure except that its `rates` contains
only sourced non-USD rows. Its original INR value and timestamps are unchanged.

The loader refuses unverified, duplicate, nonpositive, nonfinite, un-sourced or
un-dated rows. Add another sourced row to add another display currency. The
agent-facing `load_fx()` preserves its historical USD/INR dictionary contract,
including loading old snapshot-format files.

The browser remembers the selected currency in local storage. Money is converted
from the projection's USD values using the selected shown rate. Original INR
claims are canonicalised using their own original World Model FX event, never a
newer assumed rate. If that event is unavailable, the receipt explicitly retains
recorded INR. Rates and dates appear by headline money, each price comparison,
fix section, what-if output, and money receipts.

## GET /investigations/{id}/billing

Returns 404 for unknown/invalid IDs; 202 while no report exists. Missing or invalid
billing support returns `status: "not measured"`, a reason and no numerical
claims. A successful response has:

- `schema_version: "billing-1"`, `base: "USD"`, original run ID/company/language
  and the exact company tokenizer.
- `claims`: numeric, checked projection claims with `id`, `value`, `unit`,
  `verified`, `evidence_ids`, and a `recompute` recipe containing the formula and
  named World Model input IDs. IDs contain full tokenizer names, including `/`.
- `headline`: field name → claim ID for the company model.
- `models`: every measured tokenizer, its verified quote or an explicit missing
  price reason, field IDs, and billed/transcript composition claim IDs.
- `composition`: company-model billed and transcript rows, each naming the part,
  its tokens per conversation claim and its share claim.
- `staircase`: source chat ID, selection convention and reply-turn rows whose
  fields refer to claims. The chosen chat is the lower median by completed reply
  count, breaking ties by source chat ID. It is a real recorded conversation.
- `fixes`: independent alternatives, sorted by checked monthly saving. Each names
  source report claim, status, tested/estimated state, saving/percent/after-cost
  IDs, and `group`: `saving`, `would_cost_more` or `not_measured`. Negative savings
  are never grouped with money-saving alternatives. A fix's numeric after-cost
  does not imply its quality passed.
- `quality`: optional A/A and A/B pair records from authenticated verdict events.
  Pair IDs are distinct and their aggregates must match report passed/judged
  claims. Missing A/A is not replaced by zero or borrowed from A/B.
- `report_money`: canonical USD values of legacy report money claims which pass
  the existing checker, each with its original FX ID.
- `default_text`: native and paired English user text from the selected source
  conversation, plus chat ID and turn. This supplies the token-strip defaults.
- `records`: direct named receipt input records, including the explicit English
  selector derivation. Transitive source IDs remain in each record's supports;
  archived supporting JSONL files or the normal evidence route supply those rows.
- `dropped_claims`: financial claims rejected during the fresh source recheck.
- `limitations`: content-only pricing, translation review, cache and alternative
  scenario limits.

### Source checking

`billing_view.py` authenticates content hashes, provenance and all transitive
support. The **unmodified existing `Checker.check()`** recomputes baseline claims
from source snapshots, prices and the original FX event. An explicit derived
snapshot selects the already-measured English variant; the same checker
recomputes that baseline. The English derivation is logged with its source,
query, fetched time, time window, run ID and support ID.

`billed_tokens()` independently reconstructs native and English whole-chat
requests, including replay. `cost_usd()` reconciles both resulting USD costs
against the corresponding checked baseline values. The projection pass is
repeated from the authenticated inputs before its custom claims are emitted.
Custom `billing_view`, `billing_fix` and `report_counts` recipes describe this
projection; they are not added to the agent checker's operation allowlist.

Report money claims undergo their existing `baseline`, `hypotheses` or
`experiment` checker operations before entering a fix. After-fix input/output
splits must reconcile to that checked after-cost before they are supplied to
what-if. Archived version-1 sampled-last-turn experiment money is explicitly
non-comparable to today's whole-chat bill and receives no misleading waterfall.

Responses can reuse a checked view only when the report and the actual content
of all relevant supporting records match the cache fingerprint. Declared event
IDs alone do not permit reuse after tampering.

### Fields and formulas

For each tokenizer, IDs are `billing/<tokenizer>/<field>`. Let C = source
conversation count, R = completed replies, V = configured monthly conversations,
I/O = billed source input/output, p/q = verified USD input/output prices per
million, and E = corresponding paired English values. Source USD cost U is
`(I*p + O*q) / 1,000,000`.

| Field | Recomputed formula / source |
| --- | --- |
| `monthly_chats`, `chat_count`, `requests` | Original config volume, distinct source chat IDs, completed assistant turns |
| `monthly_usd` | U × V / C |
| `per_conversation_usd` | U / C |
| `per_1000_conversations_usd` | U / C × 1000 |
| `per_reply_usd` | U / R |
| `english_monthly_usd` | English U × V / C at the identical provider prices |
| `language_tax_usd` | (Native U − English U) × V / C |
| `language_tax_percent` | (Native U / English U − 1) × 100 |
| `cost_multiplier` | Native U / English U |
| `token_multiplier` | (Native I + O) / (English I + O); distinct from price-weighted tax |
| `resend_factor` | R / C |
| `cacheable_share` | Repeated identical system-prefix input / all billed input; no cache price assumed |
| `system_cost_share` | Existing checked system-input cost share |
| `input_price_usd`, `output_price_usd` | Verified source provider quote per million tokens |
| `input_per_conversation`, `output_per_conversation` | I / C, O / C |
| `lone_byte_share` | Sum(tokens × recorded fragment rate) / tokens across unique native text items, prompt once; missing if any rate is invalid |
| `billed/<part>/tokens_per_conversation`, `.../share` | Existing checked billed component / C and / all billed content tokens |
| `transcript/<part>/tokens_per_conversation`, `.../share` | Prompt once per conversation + user turns once + answers once; replay part is exactly zero under this convention |
| `billed_total_per_conversation`, `transcript_total_per_conversation` | Corresponding total / C |
| `staircase/<chat>/<turn>/{input,system,new_user,replayed_history,output}` | Exact source turn counts; input = system + prior history + new user turn |
| `staircase/.../{cumulative_input,transcript_so_far}` | Sum of inputs charged through that reply; versus content seen once through that answer |

Fix IDs are `billing/fix/<source-index>/{saving_usd,saving_percent,
after_monthly_usd}`. Saving is the original checked saving / its recorded FX;
percent is saving / today's monthly USD × 100; after-cost is today minus this
single alternative's saving. Reconciled `after_input_per_conversation`,
`after_output_per_conversation`, `after_input_price_usd` and
`after_output_price_usd` support independent price what-ifs. Hypotheses remain
labelled hypotheses. `billing/trust/{reported_checked,reported_dropped}` counts
original recorded checker entries and is labelled "recorded" in the UI.

Billing audit and derived evidence are JSONL under `logs/billing*.jsonl`.

## GET /tokens?text=...&tokenizer=...

Accepts nonempty text up to 2000 characters and only a tokenizer from the measured
configuration allowlist. Unknown IDs and arbitrary `file:` paths receive 422.
A missing cached tokenizer returns `ok: false` and a reason; there is no download.

`polytoken.tokens` resolves the local `tokenizer.json`, imports the existing
`indictax` adapter, compares its IDs with metadata encoding, encodes again, checks
fragment counts again, and asserts the returned display pieces join exactly to
the input. Each piece has ID, raw label, original token offsets, display span,
text, kind and fragment flag. Byte pieces can share a Unicode span; later pieces
can have empty text and display their raw label. Normalizer-discarded gaps are
explicitly non-token spans, never invented IDs.

The response supplies token count, whitespace-word count, tokens per whitespace
word, lone-byte/partial-character share, tokenizer file hash, formulas, source,
and a World Model evidence ID/provenance. Failed calls are `ok: false` rows;
successful measurements and provenance are audited in `logs/token_strip.jsonl`.

## Browser-only scenarios

Currency conversion and the clearly labelled what-if panel are the only browser
business calculations. What-if uses checked input/output tokens per conversation,
source prices, volume and explicit input/output price multipliers. The same
formula reprices each alternative only if the backend supplies a reconciled
split. Reset restores the source volume and price multipliers of one. Scenarios
never replace checked headline claims, quality, timing or recorded savings.
SVG coordinates and dot placement encode existing values; they create no new
measurements or confidence intervals. Degenerate intervals are suppressed, with
an explanation for a company having one system prompt.
