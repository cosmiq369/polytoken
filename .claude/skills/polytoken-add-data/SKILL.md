---
name: polytoken-add-data
description: Prepare and validate a user's anonymised Telugu or Hindi conversation export for PolyToken, with an explicit English-review boundary and demo/live routing.
---

# Bring conversations to PolyToken

Use for data onboarding, not general installation. Read `docs/SAMPLE_SCHEMA.md`
from the checkout before converting anything. Keep this canonical file and its
`.claude/skills/polytoken-add-data/SKILL.md` copy identical.

## Interview first

Ask together: what bot and industry; chat or voice channel; Telugu/Hindi and script
mix; where the conversations are stored and their export format; approximate rows,
chats and size; whether they are anonymised; whether paired English translations
exist and who reviewed them; and whether Zetaris, PostgreSQL, an NVIDIA key and
candidate tokenizer caches are available. Ask for the user's working-folder path.
Do not ask them to paste credentials or private conversations into chat.

## Convert locally

Write a small conversion script and its output in the user's own working folder,
**outside this repository**. Inspect only the export needed for mapping, and keep
conversion entirely local: no model API, translation service or data upload. Never
copy user data into the bundled sample files or committed logs. Preserve chat
boundaries and alternating roles, native text and paired English. Map to `chat_id`,
`turn`, `role`, `text_native`, `text_en`, `lang` and optional `review_status`.
Use opaque local chat IDs instead of names, phone numbers or addresses. Tell the
user to anonymise content; conversion is not a promise of automatic PII removal.

Respect one MiB / 500 turns, at least two turns per chat, and the schema's other
limits. For a larger export, agree which complete chats form the sample; never
silently truncate messages or label a convenience sample representative.

## English baseline and review

Use the user's reviewed English when available and record who reviewed it in a
local companion note. If absent, ask for explicit consent before drafting English;
state the intended local drafting method and any limitations. Never send their
export to a service as part of conversion. Mark every draft `review_status:
pending` and say the comparison remains unverified until a native reviewer signs
off. Never label machine translation reviewed. Do not invent missing turns or
English text without that consent. If translation cannot be drafted locally,
stop that part and ask the user to supply English.

The launcher deliberately resets uploaded review status to pending, even if the
export asserts reviewed. Structural validation cannot attest semantic equivalence;
retain the user's review record separately and explain this conservative label.

## Validate without displaying conversations

From the clone root, run:

```sh
.venv/bin/polytoken validate-sample /absolute/user-folder/sample.jsonl --language te
# Use --language hi for Hindi; CSV with the same columns is also accepted.
```

The command reuses the launcher's validator, prints row/chat counts on success or
structural errors on failure, never echoes conversation text, and logs only
validation metadata to `logs/sample_validation.jsonl`. Resolve exact structural
errors in the conversion script and rerun. Do not change the validator to accept
invalid data. Report the counts and pending review status, never sample contents.

## Run and interpret

Demo mode replays checked saved runs on synthetic companies. It cannot investigate
an upload; form edits do not change the archived findings. For live mode, follow
`skills/polytoken-setup/SKILL.md`, preserving its setup and permission boundaries,
and run `.venv/bin/polytoken doctor --live`. A green doctor is a service probe,
not proof of an uploaded investigation.

Start `.venv/bin/polytoken serve`, then **New investigation → Upload JSONL or CSV**.
Enter company, industry, channel, language, real monthly conversation volume,
candidate models and shared system instructions. Explain the transfer before Run:
the app writes the configured PostgreSQL, Zetaris reads those sources, World Model
stores sourced observations locally, and live planning sends workload summaries
to NVIDIA. Remote data services receive the configured data. Upload is a separate
step from the local-only conversion. Do not send a user's private sample without
their instruction to run it. Cached candidate tokenizers run locally; no silent
downloads. `polytoken investigate --company raitu` runs a bundled company and does
**not** accept arbitrary file uploads; use the UI for custom data.

Wait for a complete report and checked claims before calling the upload verified.
Record the run ID, status and checker outcome without conversation text. Explain
that checked means arithmetic and evidence provenance were recomputed; it does not
prove translation fidelity, model quality or voice latency. Prices are dated
quotes and costs reconstruct content at the stated volume, not an invoice.
Quality remains **verify on your sample**. Missing evidence stays unavailable.
Report failures honestly and stop after the requested onboarding.
