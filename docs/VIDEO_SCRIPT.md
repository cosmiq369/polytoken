# PolyToken narrated demo

1920×1080 · dark theme · INR · 2× replay of recorded live investigations. No provider calls occur during playback. The speech is AI-generated with Mohan’s configured cloned voice, using ElevenLabs Multilingual v2.

## Scene narration

### S01 — hook

Two Indian AI teams. Same models, same prices. One should pick Llama. The other would pay two and a half times more for it. PolyToken tells you which team you are, and proves why.

### S02 — the cause

The reason is the tokenizer. This Telugu sentence is a hundred and two tokens on Llama, most of them single bytes, and seventeen on Sarvam. Type the same thing in Tenglish, and Llama needs barely more than English. How your users write decides your bill.

### S03 — the agent at work

This is Raitu Mitra, a fictional Telugu voice assistant for farmers. I ask PolyToken which model fits. Nemotron plans each step and says why. It reads the company's conversations only through Zetaris: chats, configuration, token counts and verified prices, through federated SQL. Every observation lands in the Meterless World Model with its source and time. On the service map, each call lights up with its latency.

### S04 — the answer

The profile is all Telugu script, straight from speech recognition. Llama 3.1 8B has the lowest price per token, but on this traffic it needs five times the English tokens, so it costs two point six times the best fit. Gemma 3 4B wins, at about a hundred and forty rupees a month in estimated content cost. And PolyToken stays honest: voice latency isn't verified yet, so this is a cost recommendation, with quality to check on your own sample.

### S05 — four companies

Now four companies. Samudra and Paisa, whose users type Tenglish and Hinglish: Llama 8B is the cheapest fit. Swara and Raitu, voice agents in Hindi and Telugu: Gemma wins. The cheapest model depends on how your users write.

### S06 — trust

Every number opens its receipt: the formula, the inputs, the query and when it was fetched. A deterministic checker recomputes every claim from raw evidence before you see it, and drops anything it can't prove.

### S07 — close

Zetaris for the data. Meterless for memory and evidence. NVIDIA Nemotron for reasoning. PolyToken: the model-fit advisor for Indian-language AI. Every token accounted for.

## Evidence and editorial corrections

The prompt’s “real conversations” is corrected to fictional company conversations, and “one federated query” to federated SQL: the saved investigations each use several SQL calls. Raitu’s amount is explicitly an estimated content cost. These wording changes preserve the requested story without overstating evidence.

The token-strip example is `samudra-023`, turn 1, from [the historical v2 fictional corpus](../data/demo/v2/samudra_chats.jsonl): “నేను దీవి ప్లాన్ వాడుతున్నాను. బిల్లులో ఖర్చు అర్థం కాలేదు.” Independent local encodings verify 102 Llama 3.2 tokens and 17 Sarvam tokens. The illustrative Tenglish version is “Nenu Deevi plan use chestunna. Bill lo charge ardham kaledu.”: 19 Llama tokens, against 17 for the saved English translation. This is a local token-boundary demonstration, not the current Raitu sample; native review is pending. [Measured receipts](../logs/sample/video_token_strip.jsonl).

All company costs and ratios are recomputed from authenticated reports by [prepare_evidence.py](../scripts/video/prepare_evidence.py). [Derived values and exact claim IDs](deck/evidence.json) · [Raitu checked report](../logs/sample/agent_raitu_model_fit_report.json) · [FX receipt](../data/reference/fx.json).

Speech uses [ElevenLabs timing alignment](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) for the captions. A small pitch-preserving pace adjustment is reflected in every timestamp. Deck footage appears only in the hook and close; the opening title is two seconds.
