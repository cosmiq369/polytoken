# PROMPT-10A completion

## Ready

The sidebar now opens a structured **New investigation** brief: company, industry,
chat/voice, Telugu/Hindi, monthly conversations, priced candidate models, display
currency, reply target, shared system instructions and JSONL/CSV or bundled samples.
The [schema](SAMPLE_SCHEMA.md) and downloadable template describe paired English
baselines, limits and language/turn validation. Invalid requests do not echo data.

`POST /investigations` now supports that brief. A demo bundled sample returns a
checked saved run and the UI consumes its `/events` SSE stream, labelled **Replay
of a saved run**, with playback defaulting to **2×**. Form edits do not recalculate
archived results. Demo uploads are blocked with **Live mode needed** before sending
a run request; the API independently enforces the same boundary.

The live composition root can ingest submitted data into a generated, isolated
PostgreSQL schema, register its views in Zetaris, read it through Zetaris, measure
actual cached tokenizer encodings, persist batches, then run the existing bounded
agent. It preserves the four bundled sources. A fake SQL/tokenizer/generator test
exercises this entire path through the real runner, checker and SSE report. Newly
completed uploaded companies retain their identity in history and model-fit views.
**An actual end-to-end uploaded-data live run is not yet verified.** No successful
live-upload claim or artificial report is shown.

The [pre-change audit](ASK_AUDIT.md) found that all twelve questions retained the
same plan/tool calls and domain numbers against the blank baseline. Demo testing
used Chromium and the old box; live testing used the frozen original production
runner, after healthy service probes. Only execution accounting changed. The old
launcher question box was removed.

**Ask the evidence** is available on Companies and run pages, with suggestion chips,
a text input and explicit scope. Its deterministic router has nine intents. It
reads saved reports and authenticated World Model evidence, rechecks every returned
fact, and returns fixed refusals for unsupported/secret/injection requests. It
makes no model or external tool calls. Hypothetical volume is separately identified
as an assumption, with its own checked recipe and receipt. The [twenty-question
table](ASK_EVIDENCE_TESTS.md) includes rewordings, off-scope requests and injections.

The token strip has **Telugu (native script)** and **Tenglish (Telugu in English
letters + English words)**, paired per-tokenizer counts, ratios and one-click
comparison. Text and encodings are unchanged existing video receipts. Both are
labelled **unreviewed**: there is no recorded Mohan approval of this triplet's
semantic equivalence. The available native review concerns generated reply pairs,
not this English/native/Tenglish set; inventing a new translation would not fix it.
On Llama 3.2 the displayed sentence has native 102 / English 17 = **6.00×**, and
Tenglish 19 / English 17 = **1.117647…×**. These are not the older corpus averages.

The [canonical setup skill](../skills/polytoken-setup/SKILL.md) and identical Claude
copy interview the user, show dry runs, require approval for network installs and
remote actions, preserve existing data and keep secret entry in a local editor.
AGENTS.md and README link to it. It documents the actual sponsor distribution and
private registry access, without redistributing images or assuming a licence.
`polytoken doctor` is offline-first; `--live` adds bounded probes. Meterless is our
local implementation of the pinned reference architecture, **not an installable
Meterless dependency**. The independently installed harness retains its Git pin.

## Validation

- `.venv/bin/python -m pytest -q`: **280 passed, 8 skipped** (live opt-in tests).
- Targeted new functionality: **49 passed**; uploaded-company follow-up plus console
  and model-fit checks: **36 passed**.
- `NODE_PATH=<bundled node_modules> node web/check-launcher.cjs`: **passed** against
  the actual loopback demo server. It verifies structured submission, SSE replay,
  unchanged archived volume, Companies/run Q&A, source receipts, refusal, paired
  sample counts, demo-upload blocking and responsive light/dark layouts.
- `.venv/bin/polytoken doctor --live --port 8012`: **12 checks, zero failures or
  warnings**. Includes populated Zetaris views, live/reference price agreement,
  SQL result and the production NVIDIA serving probe. Service health alone is not
  evidence of a successful new uploaded investigation.
- Setup skill frontmatter validation passed; canonical and Claude copies match.
- History/worktree secret scan found no configured secret values or provider keys.
  Screenshot review found and corrected checkbox spacing and mobile navigation
  overlap before final captures.
- Existing report numbers did not change; `docs/DECK_TEXT.md` is unchanged.

Machine-readable proof is under `logs/sample/launcher_validation.jsonl`,
`launcher_browser_validation.jsonl`, `launcher_setup_proof.jsonl`,
`launcher_live_doctor.jsonl`, `launcher_setup_doctor.jsonl`,
`ask_audit_before.jsonl`, `ask_audit_live_before.jsonl`, `ask_evidence_20.jsonl`,
`token_samples_world_events.jsonl` and `ship_secret_scan.jsonl`. Source service
probes append to `logs/doctor.jsonl`; full perturbation run logs remain in
`logs/ask-audit/`. Desktop/mobile light/dark captures are `logs/sample/launcher_*.png`.

## Fresh-clone demo proof

A local clone was created at `/tmp/polytoken-launcher-fresh` with **no `.env`**.
Provider credential environment variables were explicitly removed for these checks.
The setup interview's test profile was: macOS, installed Python, skip Docker/Zetaris,
no NVIDIA key, bundled synthetic companies. This is a validation profile, not a
claim to have interviewed a new person.

Commands actually executed:

```sh
git clone --local --no-hardlinks /Users/mohan/BuildingWealth/PolyToken /tmp/polytoken-launcher-fresh
uv venv /tmp/polytoken-launcher-fresh/.venv --python /Users/mohan/BuildingWealth/PolyToken/.venv/bin/python
cd /tmp/polytoken-launcher-fresh
uv pip install --offline --python .venv/bin/python '.[dev]'
env -u NVIDIA_API_KEY -u HF_TOKEN -u ZETARIS_PASSWORD -u COMPANY_DB_PASSWORD .venv/bin/polytoken doctor --port 8012
env -u NVIDIA_API_KEY -u HF_TOKEN -u ZETARIS_PASSWORD -u COMPANY_DB_PASSWORD .venv/bin/pytest -q
env -u NVIDIA_API_KEY -u HF_TOKEN -u ZETARIS_PASSWORD -u COMPANY_DB_PASSWORD .venv/bin/polytoken serve --demo --port 8012
POLYTOKEN_TEST_ORIGIN=http://127.0.0.1:8012 NODE_PATH=<bundled node_modules> node web/check-launcher.cjs
```

Offline installation resolved and installed 39 packages, including the exact
`indictax` Git commit, without a network install. Doctor returned **nine checks,
zero failures, two expected warnings** (missing NVIDIA key; services not probed).
The server started and the actual fresh-clone browser acceptance passed. The initial
fresh-clone suite returned **280 passed, 8 skipped in 208.39 seconds** at `a61621e`.
After locally updating and reinstalling the final implementation at `099e3f8`,
`.venv/bin/pytest -q` returned **280 passed, 8 skipped in 199.15 seconds**. The
restarted installed demo also passed the complete launcher browser acceptance.
The final secret scan checked **1,532 reachable objects plus the worktree**, with
**zero configured-secret or provider-key hits**. Evidence is in the JSONL proof.
This demonstrates a fresh source/venv installation using an existing offline
package cache and browser installation; it is not a bare-machine download test.

## Next / pending

Mohan must approve or replace the displayed Telugu/native, Tenglish and English
triplet as equivalent. A separately reviewed pure romanized variant is needed to
show all three script conditions in the narration. No Telugu or Hindi sentence was
newly authored for this change. The existing native-review verdicts are preserved.

Live uploaded-data execution, new-machine Zetaris installation, Linux/Windows host
routing, and remote Docker over SSH remain unverified. The skill's remote path is
explicitly **Roadmap**; no host or paid cloud resource was created. Live setup needs
the user's sponsor distribution/registry access, Docker, local database credentials,
NVIDIA access and cached candidate tokenizers. Human quality review and exact-model
voice latency remain pending even when infrastructure is healthy.

## Narration V2 corrections before audio

- **S1:** “Indian languages split into far more tokens” is too broad. Say **native
  Telugu/Hindi script can require more tokens on some tokenizers**; code-mixed
  traffic can be close to English, and rankings depend on the workload.
- **S2:** “Getting started takes a few minutes” is only supported for cached demo
  setup. A first Zetaris image download/start is longer. Suggested wording:
  **“Setup starts with a few questions. With no keys, replay the saved evidence.”**
- **S3:** Record the **bundled synthetic sample replay**, not an alleged successful
  real upload. The form accepts uploads for live mode, but end-to-end live upload
  remains unverified. Suggested line: **“I choose a bundled workload and press Run.
  For this video, I’m replaying its saved investigation.”** Retain the replay label.
- **S4:** ₹139, ₹363 and 2.61× remain the saved rounded content-cost scenario.
  Say **“lowest content-cost candidate”**, not an unqualified best voice model;
  Raitu has no verified exact-model/provider voice latency, and quality still
  requires verification. The approximately five-times statement is a workload
  ratio for Llama 3.1, not the token-strip sentence.
- **S5:** The displayed sentence is **6.00× native** and **1.12× Tenglish**, with
  equivalence unreviewed. **7.59×, 1.68× and 1.09×** are older corpus aggregates
  (`logs/sample/experiment01/`), not this sentence. Either show that aggregate
  source and label it as such, or use the displayed sample values. There is no
  reviewed pure romanized switch in this implementation.
- **S6:** Now supported: Companies comparisons, grounded answers with receipts,
  and fixed refusals. The two-versus-two outcome remains unchanged.
- **S7:** The **29 upstream conformance checks** statement remains supported;
  the conformance files also contain an additional local Indic-ID regression.
- **S8:** Keep the distinction between cost fit and model quality. No new quality
  or latency guarantee was added.

PROMPT-10B/video recording has not been started.
