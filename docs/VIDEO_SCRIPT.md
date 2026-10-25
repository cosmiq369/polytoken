# PolyToken model-fit demo: three-minute shot list

Use `polytoken serve --demo`. Start on Companies in dark or light mode. The recordings replay saved evidence; they make no provider calls.

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00–0:25 | Companies | “Which model fits an Indian-language product? Start with its users. These four fictional teams send different scripts, vocabulary and conversation lengths.” |
| 0:25–0:50 | Samudra Model fit | “Samudra's app users mostly type Tenglish or romanized Telugu. Llama 3.1 8B wins at ₹176 a month for 200,000 conversations; here the cheapest-per-token model is also the best fit. Open its cost receipt: model price, tokenizer counts, and the source query.” |
| 0:50–1:15 | Raitu Model fit | “Raitu receives Telugu script from a voice workflow. Here Gemma is the cheapest content-cost candidate. At 80,000 conversations, Gemma costs ₹139 a month versus ₹363 for the lowest-unit-price Llama 3.1 8B, or 2.61× the cost. Llama needs 5.03× English tokens against Gemma’s 1.35×; Llama 3.2 3B costs 16.42× the best fit. The model has not met a measured voice-latency constraint, so PolyToken withholds that deployment recommendation.” |
| 1:15–1:35 | Swara, then Paisa | “Swara's Hindi voice answers are longer. Paisa's short Hinglish messages contain product terms and numbers. At 120,000 conversations Swara’s Gemma candidate costs ₹275 per month versus ₹359 for the cheapest per token; at 300,000 Paisa’s Llama 3.1 8B costs ₹154 for both. Their profiles explain why the ranking changes.” |
| 1:35–2:05 | Activity replay and trace | “Nemotron plans each bounded step. Zetaris supplies the data. Each service call has a recorded duration. World Model keeps source evidence, H-MEM keeps profiles, and Markovian compresses the reasoning state.” |
| 2:05–2:35 | Evidence receipt | “The checker recomputes the arithmetic. No verified price means tokenizer fit only. Missing timing cannot pass a voice constraint. Quality says verify on your sample; the available hosted stand-in cannot validate another model.” |
| 2:35–3:00 | Companies and score | “Four fresh investigations, independently scored against predictions registered before data. PolyToken explains the fit and what remains to test. Every recommendation has a receipt.” |

Read any spoken figures directly from the displayed checked claims. Content-cost estimates are not invoices. The reference-corpus ratios and current-company ratios describe different samples. No secrets or configuration files should appear in the recording.

Spoken amounts and multiples derive from checked cost, ratio and `profile/monthly_conversations` claims: [Samudra](../logs/sample/agent_samudra_model_fit_report.json), [Raitu](../logs/sample/agent_raitu_model_fit_report.json), [Swara](../logs/sample/agent_swara_model_fit_report.json), [Paisa](../logs/sample/agent_paisa_model_fit_report.json). Currency receipt: [₹94.9432/USD](../data/reference/fx.json), 23 October. Monthly = USD per 1,000 × volume / 1,000; multiples use the unrounded costs.
