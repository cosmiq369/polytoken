# Conversation samples

Download [sample-template.jsonl](../web/sample-template.jsonl) from the launcher. It
contains existing synthetic Samudra turns; no new translation has been invented.
Equivalent CSV uses the same column names, a header row, and normal quoted fields.
Encode files as UTF-8. JSONL is one object per nonblank line, not a JSON array.

| Field | Meaning |
|---|---|
| `chat_id` | Local identifier, letters/digits/hyphen/underscore, up to 80 characters |
| `turn` | Consecutive integer starting at 1 within a chat, up to 100 |
| `role` | `user` or `assistant`, alternating, starting with user |
| `text_native` | Actual Telugu/Hindi/native-script/romanized/code-mixed message |
| `text_en` | English translation of the same message, reviewed by your team |
| `lang` | `te` or `hi`, matching the launcher selection |

Every chat needs at least a user turn and an assistant reply. At most 500 turns,
one MiB of UTF-8 sample data, and 4,000 characters per text. Duplicate/missing
turns, other fields (except optional `review_status`, always reset to pending),
empty paired text, wrong native-script blocks and unsupported formats are rejected.
Latin-only text is allowed for Tenglish/Hinglish. Validation cannot establish the
language or semantic equivalence of romanization; native review remains required.

The form supplies name, industry, channel, monthly conversations, currency, candidate
models, latency target and shared system instructions. Shared instructions are
used unchanged for native and English billing; supply the real shared policy or
record this as an assumption. Only models in the verified priced list are accepted.

Demo uploads show **Live mode needed** and do not run. Bundled demo samples replay
their original company, model list and volume, regardless of form edits. Live
launches copy the chosen sample into an isolated generated PostgreSQL schema,
register its projections, read it through Zetaris, and store actual local tokenizer
counts. Only successful paired batches support results. Candidate caches must be
installed during setup. The bounded agent reads configuration, chats, measurements
and prices through Zetaris; it never substitutes the template for your upload.

Use anonymised or synthetic conversations. The browser posts them only to the
loopback app. The app persists them in the configured source database and sourced
World Model logs; live planning sends workload summaries to NVIDIA. Remote Zetaris
means the data leaves this machine. No automatic redaction of personal information
is promised. Uploaded datasets have generated identifiers and are never committed
by the launcher. One bundled synthetic Telugu chat template completed through the live launcher
with 141 independently rechecked claims; see [verification and scope](LIVE_UPLOAD_STATUS.md).
This verifies that bounded local-stack case, not arbitrary exports, voice uploads
or remote deployments. Quality and native review remain pending.
