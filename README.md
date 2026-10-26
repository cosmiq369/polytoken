# PolyToken

[Bring your data](docs/BRING_YOUR_DATA.md) · [Setup skill](skills/polytoken-setup/SKILL.md) · [Add-data skill](skills/polytoken-add-data/SKILL.md)

**Which model fits your Indian-language users and your budget—and why?** PolyToken profiles the team's own conversations, measures their token counts, compares verified model/provider quotes, and explains a conditional recommendation with evidence you can inspect.

Built by **Mohan Chelluru** for Open Agent Hackathon 2026, **Track 02: The Agent That Can Explain Why**. All four companies and their forty conversations each are fictional. Translations and native review remain pending.

![Four workload profiles and their model-fit candidates](docs/images/model_fit_companies_desktop_dark.png)

**Demo video:** [Watch on YouTube](https://youtu.be/IHxXnPjBIEM) (published unlisted).

Narration is an AI voice generated from the author's own voice with ElevenLabs.

The deck is submitted through the hackathon form. Source video, audio, deck and internal prompts stay local.

## The users change the fit

A voice agent usually receives native script from speech recognition. An app can receive romanized Telugu, Tenglish or Hinglish, with English product names and numbers. That mixture, conversation history and answer length change the bill.

The pre-existing Experiment 01 measured eighteen parallel sentences. Telugu / English token ratios were:

| Written as | Llama 3.2 | Gemma 3 |
| --- | ---: | ---: |
| Telugu script | 7.59× | 1.58× |
| Romanized | 1.68× | 1.57× |
| Tenglish | 1.09× | 1.06× |

For Hindi, the corresponding Llama / Gemma ratios were 2.44× / 1.18× in Devanagari, 1.87× / 1.59× romanized, and 1.21× / 1.04× code-mixed. These are token ratios on that reference corpus, not quality, latency or current-company measurements. [Raw counts](logs/sample/experiment01/fertility.csv) · [Original results](logs/sample/experiment01/fertility.md) · [Provenance](logs/sample/experiment01_provenance.jsonl).

## Four fresh live investigations

| Company / monthly volume | Best content-cost fit / month | Cheapest per token / month | × best fit |
| --- | --- | --- | ---: |
| [Samudra Telecom](logs/sample/agent_samudra_model_fit_report.json) / 200,000 | Llama-3.1-8B-Instruct: ₹176 ($1.86) | Llama-3.1-8B-Instruct: ₹176 ($1.86) | 1.00× |
| [Swara Care](logs/sample/agent_swara_model_fit_report.json) / 120,000 | gemma-3-4b-it: ₹275 ($2.89) | Llama-3.1-8B-Instruct: ₹359 ($3.78) | 1.31× |
| [Raitu Mitra](logs/sample/agent_raitu_model_fit_report.json) / 80,000 | gemma-3-4b-it: ₹139 ($1.47) | Llama-3.1-8B-Instruct: ₹363 ($3.83) | 2.61× |
| [Paisa Saathi](logs/sample/agent_paisa_model_fit_report.json) / 300,000 | Llama-3.1-8B-Instruct: ₹154 ($1.62) | Llama-3.1-8B-Instruct: ₹154 ($1.62) | 1.00× |

These dated provider scenarios reconstruct completed conversations with each model's own tokenizer and price, including history replay. They exclude provider chat templates, retries, taxes and unpublished cache discounts; the small totals are content-token estimates, not invoices. USD prices retain their original fetch dates. All eight tokenizers completed on all four workloads. Eight priced models are ranked separately, with all eleven provider quotes available for inspection; four unpriced families show **tokenizer fit only**.

The predictions registered in the [25 October addendum](docs/CONTRACT.md) passed for each company's dominant script, cost candidate and constraint handling. Quality remains **verify on your sample**. Neither voice candidate has exact-model/provider/workload latency evidence, so neither receives a voice-qualified recommendation. [Recomputed score and top-three rankings](logs/sample/model_fit_score.md) · [Machine-readable score](logs/sample/model_fit_score.jsonl) · [Full completion report](docs/MODEL_FIT_COMPLETION.md).

The Model fit tab shows the script mix, conversation shape, answer share, ranked models, runner-up, and the largest tokenizer penalty among cheap-per-token models to avoid. Every figure opens a source receipt. The Companies view compares monthly cost at each company’s own volume. For Raitu, Llama 3.1 8B’s lowest unit quote still costs **2.61×** Gemma, with **5.03×** English tokens versus **1.35×**; Llama 3.2 3B costs **16.42×** the best fit. [Checked Raitu cost and ratio claims](logs/sample/agent_raitu_model_fit_report.json). Monthly = checked USD / 1,000 × checked monthly conversations / 1,000; “× best fit” divides checked model cost by the lowest checked cost. INR uses the [recorded ₹94.9432/USD rate, dated 23 October](data/reference/fx.json); the currency switch shows its source. “Cheap per token” means the lower half of models by the price of an equal input/output token basket. [Replay recording](docs/images/model_fit_replay.webm).

## How the evidence becomes advice

**Zetaris is the data layer.** Configuration, chats, measurements, reference sentences and prices are read through SQL. Public projections handle this connector's single-schema restriction; the price table uses a locally served REST source. PostgreSQL access is confined to setup and measurement writes. [Federation query](sql/token_ratio_by_part.sql) · [New federation evidence](logs/sample/model_fit_measurements/federation.jsonl) · [Live SQL audit](logs/sample/model_fit_v1_audit_zetaris_queries.jsonl).

**NVIDIA Nemotron is the brain.** One injected generator handles planning and contextual judging; model name, base URL and rate limit come from `.env`. The loop uses physical-attempt budgets, bounded retries and one shared limiter. Only GPT-OSS passed the recorded serving probe. The retained A/A-controlled protocol can test an answer-length hypothesis on that stand-in, but cannot establish quality or latency for a different model/provider. Fresh model-fit runs collect reasoning and service-call timings; they do not pretend to be new quality experiments. [Generator](src/polytoken/llm.py) · [Serving evidence](logs/sample/hosted_probe.jsonl) · [Fresh calls](logs/sample/model_fit_v1_audit_llm_calls.jsonl).

**Meterless runs in-process as in-repo Python against a pinned reference specification, not an installed library.** World Model stores observations with source, query, time window and fetch time. H-MEM retains sourced company profiles and historical findings; replaced datasets do not inherit old findings. Markovian carries compressed state across bounded chunks and records projected versus actual token accounting. Its savings are a history-replay counterfactual, not a measured second execution. [Attribution and conformance](docs/METERLESS.md) · [New chunk accounting](logs/sample/model_fit_v1_audit_agent_markovian.jsonl).

**The deterministic checker gates every reported number.** It authenticates evidence and recomputes profiles, token ratios and per-model costs. Recommendations are rebuilt from those checked claims on replay. Missing prices never become zero cost; missing or mismatched timing never satisfies a voice constraint. [Calculator](src/polytoken/model_fit.py) · [Checker](src/polytoken/checker.py) · [Checker audit](logs/sample/model_fit_v1_audit_checker.jsonl).

## Run it

Python 3.10+, Git and the pinned `indictax` dependency are required. For live investigations, configure the local Zetaris stack, PostgreSQL demo source, and NVIDIA account. Node/Playwright are browser-test tools, not application dependencies. Run from the repository root.

```sh
uv venv .venv
source .venv/bin/activate
uv pip install '.[dev]'
cp .env.example .env
```

Fill the variable names in `.env.example` locally; never commit credentials. The harness is imported from the pinned public Git dependency, with an optional editable development override. [Declarations](docs/DECLARATIONS.md).

For the saved, offline demo:

```sh
polytoken serve --demo
```

Open [PolyToken](http://127.0.0.1:8000). All four replays include fresh recorded call timings. Older archives explicitly say “Timing unavailable” where no spans were captured.

For live setup, start the sponsor's Zetaris distribution and run its `./verify.sh`, then:

```sh
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
python scripts/seed_company_db.py
python scripts/serve_reference.py  # keep running in a separate terminal
python scripts/register_zetaris_sources.py
polytoken measure --company all
polytoken doctor --live
polytoken serve
```

```sh
polytoken investigate --company raitu --sample-suffix model_fit
# Optional, separately bounded controlled stand-in experiment:
polytoken investigate --company swara --test-answer-length --sample-suffix quality_sample
python -m pytest -q
python -m pytest -q -m live
polytoken score
```

## Limits and history

Script detection is a Unicode/lexicon heuristic with an unclassified bucket; English-term share means recognized domain terms. The data is synthetic and template-based, and translations remain unreviewed. Shared tokenizer families imply neither equal model quality nor equal latency. Observed latency samples are not SLAs. No unpublished cache discount or generated-answer improvement is invented.

All audit and provenance records go to `logs/`, with curated evidence committed in [logs/sample](logs/sample/). [Complete model-fit evidence closure](logs/sample/model_fit_v1_world_events.jsonl.gz) includes the first partial run as well as all four completed runs. Previous datasets and logs remain archived. Model-fit scoring is offline; the agent never reads the contract or scorer.

Cursor was not used. Codex and Claude assisted development. [Submission](docs/SUBMISSION.md) · [Metadata](metadata.json) · [MIT licence](LICENSE) · [Deck text](docs/DECK_TEXT.md).

## Set up with your coding agent

Paste: **“Read skills/polytoken-setup/SKILL.md and set up this PolyToken clone with me; ask the setup questions first.”**

The [setup skill](skills/polytoken-setup/SKILL.md) covers the key-free demo, the sponsor's local Zetaris distribution, the app database, local secret entry, and diagnostics. `polytoken doctor` checks the installation offline; `polytoken doctor --live` adds bounded service probes. Meterless engines are local implementations of a pinned reference architecture, not an extra package to install. Remote Docker over SSH remains an explicitly unverified roadmap path.

Use **New investigation** to enter a workload and choose a bundled sample or a paired JSONL/CSV file ([schema and template](docs/SAMPLE_SCHEMA.md)). Demo runs replay checked saved evidence and retain its original settings; uploaded files require live mode. Ask the evidence answers a limited set of questions from authenticated saved claims and refuses unsupported requests.

## Bring your data

Use the [add-data guide](docs/BRING_YOUR_DATA.md) and [coding-agent skill](skills/polytoken-add-data/SKILL.md) to map an anonymised export locally and validate it with `polytoken validate-sample FILE --language te` (or `hi`). Use reviewed English or explicitly consent to a draft that remains pending native review. Validation reports counts and structural errors without echoing conversation text.

Demo mode replays checked saved runs on synthetic companies. Uploads need live mode; one live upload of the bundled synthetic Telugu chat template completed with 141 independently rechecked claims. This verifies that bounded local-stack case, not arbitrary data, voice or remote deployments ([verification](docs/LIVE_UPLOAD_STATUS.md)). Live planning sends workload summaries to NVIDIA; imported data goes to your configured PostgreSQL and Zetaris stack. The app's **How it works** page explains these boundaries.
