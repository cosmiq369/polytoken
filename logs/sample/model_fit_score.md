# Model-fit addendum score

The scorer recomputes claims and recommendations from authenticated evidence. It is not imported by the agent. Expected winners were registered before data; failures remain visible.

| Company | Profile prediction | Model prediction | Constraint handling | Candidate |
| --- | --- | --- | --- | --- |
| samudra | pass | pass | pass | meta-llama/Llama-3.1-8B-Instruct |
| swara | pass | pass | pass | google/gemma-3-4b-it |
| raitu | pass | pass | pass | google/gemma-3-4b-it |
| paisa | pass | pass | pass | meta-llama/Llama-3.1-8B-Instruct |

## samudra

Report: [agent_samudra_model_fit_report.json](agent_samudra_model_fit_report.json). Quality: verify on your sample. Conditional on quality verification.

| Model | Provider | USD / 1,000 conversations | Tokens / English |
| --- | --- | ---: | ---: |
| meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | 0.009283 | 1.542× |
| google/gemma-3-4b-it | Parasail (via OpenRouter) | 0.012194 | 1.195× |
| openai/gpt-oss-20b | DeepInfra (via OpenRouter) | 0.014410 | 1.203× |

## swara

Report: [agent_swara_model_fit_report.json](agent_swara_model_fit_report.json). Quality: verify on your sample. No model has verified latency for this voice workload.

| Model | Provider | USD / 1,000 conversations | Tokens / English |
| --- | --- | ---: | ---: |
| google/gemma-3-4b-it | Parasail (via OpenRouter) | 0.024124 | 1.112× |
| meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | 0.031489 | 2.189× |
| google/gemma-3-12b-it | DeepInfra (via OpenRouter) | 0.040553 | 1.112× |

## raitu

Report: [agent_raitu_model_fit_report.json](agent_raitu_model_fit_report.json). Quality: verify on your sample. No model has verified latency for this voice workload.

| Model | Provider | USD / 1,000 conversations | Tokens / English |
| --- | --- | ---: | ---: |
| google/gemma-3-4b-it | Parasail (via OpenRouter) | 0.018329 | 1.354× |
| google/gemma-3-12b-it | DeepInfra (via OpenRouter) | 0.028890 | 1.354× |
| openai/gpt-oss-20b | DeepInfra (via OpenRouter) | 0.031033 | 1.417× |

## paisa

Report: [agent_paisa_model_fit_report.json](agent_paisa_model_fit_report.json). Quality: verify on your sample. Conditional on quality verification.

| Model | Provider | USD / 1,000 conversations | Tokens / English |
| --- | --- | ---: | ---: |
| meta-llama/Llama-3.1-8B-Instruct | DeepInfra (via OpenRouter) | 0.005411 | 1.088× |
| google/gemma-3-4b-it | Parasail (via OpenRouter) | 0.009302 | 1.044× |
| openai/gpt-oss-20b | DeepInfra (via OpenRouter) | 0.010604 | 1.061× |
