# Vendored reference data

Copied without modification on 24 Oct 2026; these are data/configuration, not
harness implementation code. Attribution: Mohan Chelluru, indic-inference-tax.
The runtime harness is pinned to
`cosmiq369/indic-inference-tax@0f61ec90ae49082d0fef7a21774e746fe17ed1cf`.

| Repository path | Origin | Licence | SHA-256 |
|---|---|---|---|
| `data/reference/seed_v0_corrected.jsonl` | Author's local `../solve-it/data/prompts/seed_v0_corrected.jsonl`; corrected corpus is not in the public pinned commit | CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ | `bc4166f22c9839462e0231aa919ad4287026bdc127d32d4f2eabd7b4a86e0292` |
| `configs/tokenizers.yaml` | `../solve-it/configs/tokenizers.yaml`, byte-identical to https://github.com/cosmiq369/indic-inference-tax/blob/0f61ec90ae49082d0fef7a21774e746fe17ed1cf/configs/tokenizers.yaml | MIT | `1678b1de0327de50adc481a7c3ba384be06dfb05a2d1ceefbace383620b08424` |

Original review metadata is preserved; vendoring is not translation approval.


## Model-fit additions — 25 Oct 2026

The four Claude-verified, schema-valid quotes in
`docs/review/2026-10-25/prices_additions.json` are included verbatim in prices.json.
They are dated provider quotes, not guaranteed current invoices. Each model/provider
is ranked separately using its input and output rate and measured workload counts.
Llama 3.x (3.1 8B, 3.2 3B and 3.3 70B) share the Llama 3 tokenizer family;
Gemma 3 sizes (4B, 12B, 27B) share the Gemma 3 tokenizer family. Family reuse is
for content token estimation only: model-specific templates, serving latency and
quality are unverified and cannot be inherited from the tokenizer or another size.
The eight configured tokenizer specimens are unchanged. Previous dataset inputs
are preserved under data/demo/v2; all new paired text remains pending review.
