# PolyToken submission

Demo video: [Watch on YouTube](https://youtu.be/IHxXnPjBIEM) (published unlisted).

Narration is an AI voice generated from the author's own voice with ElevenLabs.

## Sponsor technology explanation

PolyToken answers: “Our bot or voice agent works in an Indian language. Which model fits our users and our budget, and why?” It profiles the company's conversation mix and shape, compares each priced model using its measured tokenizer counts, and produces a conditional recommendation, runner-up and cost-based avoidance explanation. The four demo companies are fictional; quality remains to verify on a real sample.

**Zetaris** is the data layer for company configuration, chats, token measurements, reference sentences and verified prices. The federation joins company and measurement views with reference coverage and a REST price table. Direct PostgreSQL access is limited to setup and measurement writes. The installed connector exposes public projections to handle its schema restriction. All four companies and eight tokenizers were remeasured; the federation verified 96 company/tokenizer/part groups. [SQL evidence](../logs/sample/model_fit_measurements/federation.jsonl).

**Meterless** provides the pinned reference specification; PolyToken implements its engines as in-repo Python running in-process. It is not an installed Meterless library. World Model stores observations with source, query, time window and fetch time. H-MEM retains sourced profiles and findings, separating the replacement dataset from old findings. Markovian compresses carried state across bounded reasoning chunks and logs projected versus actual token accounting. The history-replay comparison is a counterfactual, not a second measured run. [Attribution and conformance](METERLESS.md).

**NVIDIA** provides the API. Nemotron plans and judges through one injected generator, configured by environment. Shared rate limiting, physical-attempt budgets and bounded retries constrain execution. Only GPT-OSS passed the recorded serving probe. The retained A/A-controlled quality protocol can test a stand-in, but cannot validate another model/provider. These new investigations collect fresh reasoning and service timings; candidate voice latency remains unverified. [Call audit](../logs/sample/model_fit_v1_audit_llm_calls.jsonl).

The deterministic checker recomputes every numeric claim from authenticated evidence. Model-fit replay reconstructs the ranking and recommendation rather than trusting saved labels. Unknown prices remain unavailable; unknown timing never qualifies a voice model. All four pre-registered profile and cost-candidate predictions passed; none establishes production quality. [Addendum score](../logs/sample/model_fit_score.md).

| Company / monthly conversations | Best content-cost fit / month | Cheapest per token / month | × best fit |
| --- | --- | --- | ---: |
| [Samudra Telecom](../logs/sample/agent_samudra_model_fit_report.json) / 200,000 | Llama 3.1 8B: ₹176 | Llama 3.1 8B: ₹176 | 1.00× |
| [Swara Care](../logs/sample/agent_swara_model_fit_report.json) / 120,000 | Gemma 3 4B: ₹275 | Llama 3.1 8B: ₹359 | 1.31× |
| [Raitu Mitra](../logs/sample/agent_raitu_model_fit_report.json) / 80,000 | Gemma 3 4B: ₹139 | Llama 3.1 8B: ₹363 | 2.61× |
| [Paisa Saathi](../logs/sample/agent_paisa_model_fit_report.json) / 300,000 | Llama 3.1 8B: ₹154 | Llama 3.1 8B: ₹154 | 1.00× |

Monthly = checked USD per 1,000 × checked company volume / 1,000 × the [dated INR/USD rate](../data/reference/fx.json). Multiples use unrounded costs. These are content estimates, not invoices; templates, retries, taxes and unpublished cache discounts are excluded. Both voice candidates lack matched latency evidence, and all quality remains to verify. Exact claims and recomputation (local submission material).

**Cursor was not used.** Codex and Claude assisted development. The pre-existing measurement harness and Experiment 01 are disclosed in [DECLARATIONS.md](DECLARATIONS.md).

## Project summary

PolyToken advises teams choosing models for Indian-language bots and voice agents. The same language can arrive as native-script speech transcripts, romanized chat or mixed-language product messages. Nemotron investigates fictional companies through Zetaris SQL, reconstructs conversation billing with each model's measured tokenizer, and compares verified provider quotes. Independently implemented Meterless architectures preserve sourced evidence, company memory and compressed reasoning state. A deterministic checker recomputes every number before the Model fit and Companies screens display it with source receipts. Samudra Telecom and Paisa Saathi favor the low-price Llama quote on their Latin-script mixtures; Swara Care and Raitu Mitra favor Gemma on native-script voice workloads. Voice latency remains unverified, so those are cost candidates rather than qualified deployment recommendations. Quality must be verified on a real sample. The agent explains both the recommendation and the evidence still missing.

## Reproduce and bring your data

Demo mode replays checked saved runs on synthetic companies. The [setup skill](../skills/polytoken-setup/SKILL.md) interviews the user and guides installation; the [add-data skill](../skills/polytoken-add-data/SKILL.md) maps anonymised exports locally and validates paired JSONL/CSV. Uploaded samples need live mode. One bundled synthetic Telugu chat template was uploaded through the live launcher and completed with 141 independently rechecked claims ([verification and limits](LIVE_UPLOAD_STATUS.md)). Arbitrary exports, voice uploads and remote deployments remain unverified. Live reasoning sends workload summaries to NVIDIA; imported data goes to the configured PostgreSQL and Zetaris stack.

Candidate tokenizers run locally from cached files. The standard model-fit investigation does not call the candidate models. The controlled hosted quality experiment is separate, and its GPT-OSS stand-in does not establish candidate quality or voice latency. The app’s How it works view shows the runtime boundaries and checked Ask path.

The deck is submitted through the hackathon form. Presentation artifacts stay local.
