# PolyToken — model-fit pitch text

## 1. Which model fits your users?
Indian-language bots and voice agents need a model decision grounded in how people actually communicate.

## 2. The same language has different shapes
Native-script speech transcripts, romanized messages and code-mixed product vocabulary tokenize differently. Conversation history and answer length also affect cost. Use the dated Experiment 01 table in the README as the reference example, not as a company measurement.

## 3. Four companies, four workload profiles
Samudra Telecom: Tenglish and romanized app support. Swara Care: Hindi voice with long spoken answers. Raitu Mitra: Telugu voice with rural vocabulary. Paisa Saathi: short Hinglish fintech chat. All data is fictional and review is pending.

## 4. Show the Companies screen
Llama 3.1 8B is the cheapest quoted candidate for Samudra and Paisa. Gemma 3 4B is the cheapest candidate for Swara and Raitu. Use checked costs from logs/sample/model_fit_score.jsonl. Voice latency remains unverified.

## 5. Explain the decision
The Model fit tab links script mix, conversation shape, model-specific measured tokens and dated provider quotes. It ranks models, names a runner-up and explains a higher-cost alternative to avoid on cost alone.

## 6. Evidence before recommendation
The checker authenticates and recomputes each number. Missing prices produce tokenizer-fit-only entries. Missing exact-model/provider/workload timing cannot satisfy a voice constraint. Quality stays “verify on your sample.”

## 7. Sponsor architecture
Zetaris: federated SQL data layer. NVIDIA: Nemotron planning and judging through one configured generator. Meterless: independent World Model, H-MEM and Markovian reference implementations. Cursor was not used.

## 8. Honest limits and next evidence
Synthetic templates, unreviewed translations, content-only cost estimates and shared tokenizer families. Only GPT-OSS passed the serving probe. Keep the A/A-controlled quality protocol, but do not transfer its stand-in results to another model.

## 9. Watch the agent, inspect the receipt
Replay fresh timing events, open a source query, and compare the four model-fit decisions. The offline scorer checks the dated addendum; the agent never sees its planted expectations.
