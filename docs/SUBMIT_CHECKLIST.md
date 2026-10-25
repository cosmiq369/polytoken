# Submission checklist — Mohan reviews and submits

Deadline: **27 October 2026, 23:45 UTC / 28 October, 05:15 IST** (project brief).

## Review the deliverables

- [ ] Watch [PolyToken_demo.mp4](video/PolyToken_demo.mp4), with audio and once muted. Check cloned-voice pronunciation of Raitu, Zetaris, Nemotron and the Indian-language names.
- [ ] Scan [the video contact sheet](video/contact_sheet.png) and [the deck PDF](deck/PolyToken_deck.pdf). [Editable PowerPoint](deck/PolyToken_deck.pptx) and [slide PNGs](deck/slides/) are included.
- [ ] Confirm the fictional-data, content-cost, quality and voice-latency caveats are visible and understandable. Review [exact narration](VIDEO_SCRIPT.md) and [checked figures](deck/evidence.json).
- [ ] Upload the MP4 as **unlisted YouTube** or a viewable Drive video. Upload [the SRT](video/PolyToken_demo.srt) if supported. Test the link in a signed-out browser.
- [ ] Paste the resulting URL into `demo_video_url` in [metadata.json](../metadata.json). Set `demo_video_url_status` to `uploaded`; replace **Public video URL: PENDING UPLOAD** in [README](../README.md) and [SUBMISSION](SUBMISSION.md) with the link, then commit and push those edits.
- [ ] Make [the GitHub repository](https://github.com/cosmiq369/polytoken) public after review. Confirm the video, PDF, evidence paths and pinned public dependency work without signing in.
- [ ] Attach **[PolyToken_deck.pdf](deck/PolyToken_deck.pdf)** to the form. Submit the repository URL and uploaded video URL; a repository-relative video path is not a public video URL.

## Form fields to paste

**Project:** PolyToken  
**Track:** 02 — The Agent That Can Explain Why  
**Builder:** Mohan Chelluru  
**Repository:** https://github.com/cosmiq369/polytoken  
**License:** MIT

**Summary**

PolyToken is a model-fit advisor for Indian-language AI. A model’s price per token can hide the cost of how people write: native-script voice transcripts, romanized chat and mixed-language product messages tokenize differently. Nemotron investigates a company’s conversations through Zetaris SQL, compares measured token counts with dated provider quotes, and explains the best content-cost candidate. Independent implementations of Meterless’s World Model, H-MEM and Markovian architectures preserve evidence and reasoning state. A deterministic checker recomputes every number before it appears, with receipts for formulas, inputs and source queries. The demo uses fictional companies; quality needs sample verification and missing voice latency prevents a deployment recommendation.

**Sponsor usage**

Zetaris is the federated SQL data layer for company configuration, conversations, token measurements, reference sentences and prices. NVIDIA Nemotron plans and judges through one injected generator with shared rate limits, bounded retries and call budgets. Meterless supplies the reference architectures: we independently implement World Model for sourced observations, H-MEM for company memory, and Markovian for compressed reasoning chunks with projected and actual token accounting. All audits and provenance are recorded in JSONL. [Implementation and evidence](SUBMISSION.md).

**Cursor statement**

Cursor was not used. Codex and Claude assisted development. The pre-existing `indictax` measurement harness and Experiment 01 are disclosed in [DECLARATIONS.md](DECLARATIONS.md).

**Demonstration limits**

Fictional, template-based conversations with native review pending. Costs are dated content-token estimates, not invoices; they exclude provider templates, retries, taxes and unpublished cache discounts. Quality must be verified on a real sample. Exact-model/provider/workload voice latency is unverified. The available hosted stand-in does not validate the ranked candidate models.

## Final submission checks

- [ ] Keep credentials only in the ignored `.env`; never paste them into the form or uploaded assets.
- [ ] Check [production validation](../logs/sample/video_deck_validation.jsonl), [history secret scan](../logs/sample/ship_secret_scan.jsonl) and [completion report](VIDEO_DECK_COMPLETION.md).
- [ ] Submit before the deadline and save the confirmation. Publication, video upload and hackathon submission remain Mohan’s final actions.
