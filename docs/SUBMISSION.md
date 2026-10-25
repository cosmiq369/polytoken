# PolyToken submission

## Sponsor technology explanation

PolyToken answers: “Our bot or voice agent works in an Indian language. Which model fits our users and our budget, and why?” It profiles the company's conversation mix and shape, compares each priced model using its measured tokenizer counts, and produces a conditional recommendation, runner-up and cost-based avoidance explanation. The four demo companies are fictional; quality remains to verify on a real sample.

**Zetaris** is the data layer for company configuration, chats, token measurements, reference sentences and verified prices. The federation joins company and measurement views with reference coverage and a REST price table. Direct PostgreSQL access is limited to setup and measurement writes. The installed connector exposes public projections to handle its schema restriction. All four companies and eight tokenizers were remeasured; the federation verified 96 company/tokenizer/part groups. [SQL evidence](../logs/sample/model_fit_measurements/federation.jsonl).

**Meterless** provides the reference architectures, independently implemented in Python. World Model stores observations with source, query, time window and fetch time. H-MEM retains sourced profiles and findings, separating the replacement dataset from old findings. Markovian compresses carried state across bounded reasoning chunks and logs projected versus actual token accounting. The history-replay comparison is a counterfactual, not a second measured run. [Attribution and conformance](METERLESS.md).

**NVIDIA** provides the API. Nemotron plans and judges through one injected generator, configured by environment. Shared rate limiting, physical-attempt budgets and bounded retries constrain execution. Only GPT-OSS passed the recorded serving probe. The retained A/A-controlled quality protocol can test a stand-in, but cannot validate another model/provider. These new investigations collect fresh reasoning and service timings; candidate voice latency remains unverified. [Call audit](../logs/sample/model_fit_v1_audit_llm_calls.jsonl).

The deterministic checker recomputes every numeric claim from authenticated evidence. Model-fit replay reconstructs the ranking and recommendation rather than trusting saved labels. Unknown prices remain unavailable; unknown timing never qualifies a voice model. All four pre-registered profile and cost-candidate predictions passed; none establishes production quality. [Addendum score](../logs/sample/model_fit_score.md).

| Company / channel | Actual user mix | Cheapest cost candidate | USD / 1,000 conversations | Decision |
| --- | --- | --- | ---: | --- |
| Samudra Telecom / chat | 10.6% native, 16.0% romanized, 73.4% mixed | Llama-3.1-8B-Instruct | $0.009283 | Conditional on quality verification |
| Swara Care / voice | 100.0% native | gemma-3-4b-it | $0.024124 | Latency unverified; no qualified voice recommendation |
| Raitu Mitra / voice | 100.0% native | gemma-3-4b-it | $0.018329 | Latency unverified; no qualified voice recommendation |
| Paisa Saathi / chat | 100.0% mixed | Llama-3.1-8B-Instruct | $0.005411 | Conditional on quality verification |

Table amounts are USD content estimates per thousand completed conversations, at dated provider quotes; they exclude templates, retries, taxes and unpublished cache discounts. [Evidence and top three per company](../logs/sample/model_fit_score.jsonl).

**Cursor was not used.** Codex and Claude assisted development. The pre-existing measurement harness and Experiment 01 are disclosed in [DECLARATIONS.md](DECLARATIONS.md).

## Project summary

PolyToken advises teams choosing models for Indian-language bots and voice agents. The same language can arrive as native-script speech transcripts, romanized chat or mixed-language product messages. Nemotron investigates fictional companies through Zetaris SQL, reconstructs conversation billing with each model's measured tokenizer, and compares verified provider quotes. Independently implemented Meterless architectures preserve sourced evidence, company memory and compressed reasoning state. A deterministic checker recomputes every number before the Model fit and Companies screens display it with source receipts. Samudra Telecom and Paisa Saathi favor the low-price Llama quote on their Latin-script mixtures; Swara Care and Raitu Mitra favor Gemma on native-script voice workloads. Voice latency remains unverified, so those are cost candidates rather than qualified deployment recommendations. Quality must be verified on a real sample. The agent explains both the recommendation and the evidence still missing.
