# PolyToken — final model-fit deck

Deck PDF (local submission material) · Editable PowerPoint (local submission material) · Recomputed values and claim IDs (local submission material)

## 1. PolyToken

The model-fit advisor for Indian-language AI. Which model fits your users — and why?

Open Agent Hackathon 2026 · Track 02: The Agent That Can Explain Why · Mohan Chelluru.

## 2. A price sheet cannot see how your users write

Experiment 01: Llama 3.2 uses 7.59× English tokens for Telugu script, versus 1.09× for Tenglish. Gemma 3 uses 1.58× and 1.06× respectively. These are paired reference-corpus ratios, not company measurements or quality results. [Raw counts](../logs/sample/experiment01/fertility.csv) · [Published table](../logs/sample/experiment01/fertility.md) · [Provenance](../logs/sample/experiment01_provenance.jsonl).

## 3. One decision, four workloads

Samudra Telecom: Tenglish and romanized app support. Swara Care: Hindi voice with long spoken answers. Raitu Mitra: Telugu voice with rural vocabulary. Paisa Saathi: short Hinglish fintech chat. All companies and conversations are fictional; native review is pending.

“Which model fits our users and our budget — and why?”

## 4. The agent explains the path

Understand the workload; measure paired token counts; compare dated quotes; check the arithmetic; explain the ranked cost fit and missing evidence. Nemotron plans bounded steps. Zetaris provides SQL data access. Meterless state preserves evidence, company profiles and compressed reasoning. [Implementation](../src/polytoken/agent/) · [Meterless attribution](METERLESS.md).

## 5. One reasoning loop, evidence at every boundary

Console → Nemotron loop → deterministic checker → checked report. Zetaris supplies configuration, chats, token measurements, reference sentences and prices. Independently implemented World Model, H-MEM and Markovian engines preserve sourced state. Audit and provenance records go to `logs/` as JSONL. Diagram (local submission material) · [Federation query](../sql/token_ratio_by_part.sql).

## 6. Raitu Mitra: the lowest unit price costs 2.61×

Gemma 3 4B: ₹139/month, 1.35× English tokens. Cheapest-per-token Llama 3.1 8B: ₹363/month, 5.03× English tokens. Same configured volume: 80,000 conversations/month. Voice latency is unverified; quality must be verified on a real sample. [Checked Raitu report](../logs/sample/agent_raitu_model_fit_report.json).

## 7. Four companies, four answers

| Company / monthly conversations | Best content-cost fit / month | Cheapest per token / month | × best fit |
| --- | --- | --- | ---: |
| [Samudra Telecom](../logs/sample/agent_samudra_model_fit_report.json) / 200,000 | Llama 3.1 8B: ₹176 | Llama 3.1 8B: ₹176 | 1.00× |
| [Swara Care](../logs/sample/agent_swara_model_fit_report.json) / 120,000 | Gemma 3 4B: ₹275 | Llama 3.1 8B: ₹359 | 1.31× |
| [Raitu Mitra](../logs/sample/agent_raitu_model_fit_report.json) / 80,000 | Gemma 3 4B: ₹139 | Llama 3.1 8B: ₹363 | 2.61× |
| [Paisa Saathi](../logs/sample/agent_paisa_model_fit_report.json) / 300,000 | Llama 3.1 8B: ₹154 | Llama 3.1 8B: ₹154 | 1.00× |

Monthly INR = checked USD per 1,000 × checked monthly volume / 1,000 × [dated FX rate](../data/reference/fx.json). Multiples use unrounded checked costs. Content-only estimates exclude templates, retries, taxes and unpublished cache discounts; these are not invoices. Both voice companies abstain from a latency-qualified deployment recommendation.

## 8. A claim earns its place

29 pinned Meterless conformance checks; 291 tests passed, eight live tests skipped; 12/12 pre-registered model-fit addendum checks passed. These are distinct validation measures, not model accuracy scores. Receipts expose formula, inputs, query, source and fetch time. Unsupported claims are dropped. [Conformance](METERLESS.md) · [Validation](../logs/sample/video_deck_validation.jsonl) · [Addendum score](../logs/sample/model_fit_score.jsonl).

## 9. Sponsors and their jobs

Zetaris: the federated SQL data layer. Meterless: reference architectures, independently implemented here. NVIDIA: Nemotron planning and judging through one configured generator. Cursor was not used. Codex and Claude assisted development. [Sponsor usage](SUBMISSION.md) · [Declarations](DECLARATIONS.md).

## 10. Next evidence to earn

Review native-language data, replace fictional templates with consented samples, measure exact-model/provider/workload serving latency, and run controlled quality comparisons before switching models. These are proposed next steps, not completed results. Only GPT-OSS passed the recorded serving probe; its stand-in evidence does not transfer to other models. PolyToken: every token accounted for.

## 11 · Get started with your coding agent

Clone, then ask the coding agent to run the [setup skill](../skills/polytoken-setup/SKILL.md). Demo replays saved synthetic runs; live needs the configured data stack. The [add-data skill](../skills/polytoken-add-data/SKILL.md) maps and validates paired samples and preserves pending native review. Meterless is in-repo Python against a pinned reference specification.

## 12 · Close

Which model fits your conversations — and why? What it costs. What supports it. What to verify. Built on Zetaris, Meterless and NVIDIA.
