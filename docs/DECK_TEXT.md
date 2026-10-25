# PolyToken — model-fit pitch text

## 1. Which model fits your users?
Indian-language bots and voice agents need a model decision grounded in how people actually communicate.

## 2. The same language has different shapes
Native-script speech transcripts, romanized messages and code-mixed product vocabulary tokenize differently. Conversation history and answer length also affect cost. Use the dated Experiment 01 table in the README as the reference example, not as a company measurement.

## 3. Four companies, four workload profiles
Samudra Telecom: Tenglish and romanized app support. Swara Care: Hindi voice with long spoken answers. Raitu Mitra: Telugu voice with rural vocabulary. Paisa Saathi: short Hinglish fintech chat. All data is fictional and review is pending.

## 4. Show the Companies screen
Llama 3.1 8B is the cheapest quoted candidate for Samudra and Paisa. Gemma 3 4B is the cheapest candidate for Swara and Raitu. Compare monthly cost at the company’s configured volume, with the cheapest-per-token model alongside it.

| Company / monthly volume | Best content-cost fit / month | Cheapest per token / month | × best fit |
| --- | --- | --- | ---: |
| [Samudra Telecom](../logs/sample/agent_samudra_model_fit_report.json) / 200,000 | Llama-3.1-8B-Instruct: ₹176 ($1.86) | Llama-3.1-8B-Instruct: ₹176 ($1.86) | 1.00× |
| [Swara Care](../logs/sample/agent_swara_model_fit_report.json) / 120,000 | gemma-3-4b-it: ₹275 ($2.89) | Llama-3.1-8B-Instruct: ₹359 ($3.78) | 1.31× |
| [Raitu Mitra](../logs/sample/agent_raitu_model_fit_report.json) / 80,000 | gemma-3-4b-it: ₹139 ($1.47) | Llama-3.1-8B-Instruct: ₹363 ($3.83) | 2.61× |
| [Paisa Saathi](../logs/sample/agent_paisa_model_fit_report.json) / 300,000 | Llama-3.1-8B-Instruct: ₹154 ($1.62) | Llama-3.1-8B-Instruct: ₹154 ($1.62) | 1.00× |

Monthly costs multiply the reports’ checked cost claims by `profile/monthly_conversations` / 1,000. INR uses the [dated FX receipt](../data/reference/fx.json). Voice latency remains unverified.

## 5. Explain the decision
The Model fit tab links script mix, conversation shape, model-specific measured tokens and dated provider quotes. It ranks models, names a runner-up and shows “× the best fit” and flags the highest tokenizer penalty among models in the cheaper half of equal input/output unit quotes. Raitu’s lowest-unit-price Llama 3.1 8B costs 2.61× Gemma: 5.03× English tokens versus 1.35×. Llama 3.2 3B costs 16.42× Gemma. [Checked Raitu claims](../logs/sample/agent_raitu_model_fit_report.json).

## 6. Evidence before recommendation
The checker authenticates and recomputes each number. Missing prices produce tokenizer-fit-only entries. Missing exact-model/provider/workload timing cannot satisfy a voice constraint. Quality stays “verify on your sample.”

## 7. Sponsor architecture
Zetaris: federated SQL data layer. NVIDIA: Nemotron planning and judging through one configured generator. Meterless: independent World Model, H-MEM and Markovian reference implementations. Cursor was not used.

## 8. Honest limits and next evidence
Synthetic templates, unreviewed translations, content-only cost estimates and shared tokenizer families. Only GPT-OSS passed the serving probe. Keep the A/A-controlled quality protocol, but do not transfer its stand-in results to another model.

## 9. Watch the agent, inspect the receipt
Replay fresh timing events, open a source query, and compare the four model-fit decisions. The offline scorer checks the dated addendum; the agent never sees its planted expectations.
