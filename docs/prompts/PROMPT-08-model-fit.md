# PROMPT-08: Reframe PolyToken as the model-fit advisor for Indian-language AI

Model: Astra
Effort: high
Why: a product reframe across data, agent, checker, UI and docs, with new fictional companies and fresh live runs.

## Decision (Mohan, 25 Oct)
Real teams write system prompts in English, so the "Telugu system prompt" scenario and the English-instructions fix are removed from the product. Mohan's native review rejected that fix anyway (8 same, 2 different: the changed bot declined instead of gathering details; `docs/review/2026-10-25/native_review_verdicts.md`). Keep that file and all earlier logs as history; drop the scenario, the lever, the Hindi review request and every mention of them from the agent, UI, README, deck text and submission prose.

The question PolyToken now answers: **"Our bot or voice agent works in an Indian language. Which model fits our users and our budget, and why?"**

## Why the business matters (use this evidence)
Experiment 01 (18 parallel sentences), Telugu tokens per English token:

| Written as | Llama 3.2 | Gemma 3 |
|---|---|---|
| Telugu script | 7.59x | 1.58x |
| Romanized | 1.68x | 1.57x |
| Code-mixed (Tenglish) | 1.09x | 1.06x |

Hindi: 2.44x on Llama and 1.18x on Gemma in Devanagari; 1.87x and 1.59x romanized; 1.21x and 1.04x code-mixed. A voice agent receives native script from speech recognition; an urban chat app often receives Tenglish or Hinglish. Conversation shape (turns, answer length), vocabulary (English product names, numbers) and voice latency also change the cheapest fit.

## Branch
From `feat/console` (merge it into `main` fast-forward first if tests pass, push `main`, no force). `git switch -c feat/model-fit`. Push the branch; fast-forward `main` when done and green.

## Step 0: contract addendum (before any new data)
Dated 25 Oct 2026: the demo question changes to model fit; the prompt-language lever and its planted property are withdrawn with the reason above; earlier results stay archived. New planted properties per company are listed below with the expected recommendation for each, so the scorer can check them later. The agent must not read the contract.

## Step 1: data
1. Add `docs/review/2026-10-25/prices_additions.json` (Claude-verified, schema-valid) to `data/reference/prices.json`: Llama 3.1 8B, Llama 3.3 70B, Gemma 3 12B and 27B. Tokenizer families: Llama 3.x share the Llama 3 tokenizer; Gemma 3 sizes share the Gemma 3 tokenizer; say so in SOURCES.md.
2. Fictional companies, 40 chats each, realistic for the role, fixed seed, every row `review_status = pending`, English system prompts for all:
   - **Samudra Telecom** (existing): Telugu customer-support chat in an app; replace its chats so users mostly type Tenglish and romanized Telugu, with some Telugu script. English system prompt.
   - **Swara Care** (existing): Hindi health-information voice assistant; Devanagari from speech recognition; long spoken answers; latency target.
   - **Raitu Mitra** (new): Telugu voice advisory for farmers; Telugu script from speech recognition; rural vocabulary; medium answers; latency target.
   - **Paisa Saathi** (new): Hinglish fintech chat app; code-mixed, numbers and English product terms; short answers.
   Each company's `bot_config` has its role, channel (chat or voice), monthly volume, latency target and current model.
3. Seed through the existing pipeline, register in Zetaris, measure on all eight tokenizers, verify the federation.

## Step 2: the agent finds the fit
New tools and claims, each checked:
- **Workload profile** from the company's own chats: script mix (native script, romanized, code-mixed; detect by Unicode block and Latin-script Indic words), turns per conversation, share of billed tokens in answers, share of English terms, channel and latency target.
- **Model ranking**: billed cost per 1,000 conversations for every model with a verified price, using the company's measured tokens on that model's tokenizer; the language multiplier on their actual mix; families with no verified price listed as "tokenizer fit only".
- **Recommendation**: the cheapest model that meets the constraints (latency for voice where measurable), a runner-up, and one "avoid" with the reason, each tied to profile facts ("your users speak Telugu script, which Llama splits into bytes: 7.6x"). Quality is shown as "verify on your sample" unless tested; keep the A/A-controlled quality protocol for any model that can be served (only gpt-oss passed the serving probe; say so).
- Planner levers are now model and tokenizer choice, answer length, history length and caching, not prompt language. Step text shows only checked numbers (keep the integrity fix).

## Step 3: UI
- A **Model fit** tab first in every run: the workload profile (script-mix bar, conversation shape, channel), the ranked models (cost per 1,000 conversations, multiplier, fit flags), and a recommendation card with its reasons and evidence links.
- **Companies** view: all four companies side by side with their profile and recommended model, so a viewer sees the recommendation change with the users. This is the demo's key screen.
- Remove the prompt-language fix from Billing, Quality and Overview.
- The service map shows "Timing unavailable" on replays of old logs. Run all four companies live with the new timing events and save them, so `polytoken serve --demo` replays runs with timings.

## Step 4: docs
Rewrite README, `docs/SUBMISSION.md` and `metadata.json` for the model-fit story with the four companies' results, linking evidence. Keep limits honest: fictional data, quality to verify, stand-in model. Update `polytoken score` for the new planted properties and run it.

## Tests
Script-mix detection on hand-made samples (Telugu script, romanized, Tenglish, Devanagari, Hinglish); ranking uses each model's own tokenizer counts; recommendation respects the latency constraint; no prompt-language lever remains (grep test); the integrity test. Full suite and `-m live` green.

## Stop point and report
Commits, tests, per company: profile, ranking top 3 with cost per 1,000 conversations, recommendation and reasons, score against the addendum, screenshots of Model fit and Companies (dark and light), and the replay recording refreshed. Leave `polytoken serve --demo` running.
