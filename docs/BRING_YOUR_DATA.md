# Bring your conversations

Ask your coding agent:

> Read skills/polytoken-add-data/SKILL.md and help me prepare an anonymised Telugu
> or Hindi sample for PolyToken. Ask the onboarding questions first.

The [add-data skill](../skills/polytoken-add-data/SKILL.md) interviews you about the
bot, channel, export, languages, size, anonymisation and English review. It writes
any conversion script in your own working folder, outside this repository, and
converts locally without sending your data anywhere.

Use paired native/romanized/code-mixed messages and English translations in the
[sample schema](SAMPLE_SCHEMA.md). The [bundled template](../web/sample-template.jsonl)
is synthetic and its translations are unreviewed. Use your reviewed English when
available. If you consent to a drafted translation, keep it pending until a native
reviewer signs off. PolyToken conservatively treats uploads as pending review;
validation cannot certify translation meaning.

```sh
polytoken validate-sample /absolute/your-folder/sample.jsonl --language te
# Hindi: --language hi. CSV uses the same field names.
```

Success prints row/chat counts; failure prints structural errors. No conversation
text is echoed. Samples are limited to one MiB and 500 turns. Keep complete chats
and use anonymised data. No automatic PII redaction is promised.

## Demo or live

**Demo mode replays checked saved runs on synthetic companies. Uploads need live
mode.** Changing the demo form does not change the saved settings or numbers.
Use the [setup skill](../skills/polytoken-setup/SKILL.md), then `polytoken doctor
--live` to check your installed Zetaris, PostgreSQL source and NVIDIA access.
Candidate tokenizer caches must already be installed.

Start `polytoken serve`, open **New investigation**, select **Upload JSONL or CSV**,
and enter the workload settings before Run. The local conversion did not transfer
data; Run writes your configured database, queries through Zetaris, stores sourced
World Model observations, and sends workload summaries to hosted NVIDIA reasoning.
Remote data services receive your configured data. Review this before running
private data. The CLI's `investigate --company` command selects a bundled company;
custom uploads use the launcher.

A passing doctor only verifies service probes. Full live-upload status remains
unverified until a completed uploaded run publishes checked claims.

## Read the result

Checked claims mean arithmetic was recomputed from authenticated evidence. They
do not establish translation equivalence, candidate quality or production voice
latency. Costs use dated quotes and the stated monthly volume; they are content
estimates rather than invoices. Quality remains **verify on your sample**. Inspect
source receipts and the assumptions, and use Ask the evidence for questions the
saved claims can support.

Meterless runs as in-repo Python implementations against a pinned reference
specification. It is not an installed library. See [architecture and conformance](METERLESS.md),
or open **How it works** from the app's sidebar or information button.
