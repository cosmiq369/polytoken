# Why quality scored 1/20 and 0/20

Offline diagnostic review, 25 October 2026. The original contract, prompts, generation settings, judge, evidence and scores remain unchanged. No new model calls or replacement judgments were made. This is a Codex assistant review of all paired replies, not native-speaker sign-off.

Samudra's **1/20 is contaminated by judge errors as well as real response changes**. There is no token-limit signal in its replies. Swara's **0/20 reflects substantial compression and content changes**, against an unreliable, often truncated baseline. Several Swara judge reasons are wrong even where the failure is independently defensible. Neither score measures factual accuracy against a validated answer key.

## What the score actually counts

`quality_metrics()` counts `same_facts: true` and Boolean verdicts. Both final runs contain complete generation pairs and valid Boolean verdicts for every pair. The arithmetic is correct: Samudra 1 passed / 20 judged, Swara 0 / 20. These are semantic-equivalence judgments, not a measure of how many answers are correct or useful. The checker authenticates evidence and recomputes counts; it cannot certify the judge's semantic reasoning.

The earlier Swara run had only 19 complete pairs and was **unjudged / insufficient sample**. The final recovery completed the missing pair and produced the 0/20 examined here. Those are different outcomes.

The judge instruction is: “Missing or contradicted facts mean false.” It receives the last user message and the two generated answers, with no system policies, preceding conversation, reference answer, or truncation metadata. Added details are also inconsistently treated as failures. A changed reply that corrects an invented baseline detail can therefore fail equivalence.

## Truncation evidence

These counts use **provider `usage.completion_tokens`**, not the company's tokenizer counts. The hosted stand-in is GPT-OSS 20B with low reasoning effort; provider completion usage can include reasoning and is not interchangeable with visible Telugu/Hindi token counts.

| Company / variant | Limit | Observed provider completion range | At limit | Visibly incomplete ending |
|---|---:|---:|---:|---:|
| Samudra original | 200 | 49–135 | 0/20 | 0/20 |
| Samudra changed | 200 | 66–165 | 0/20 | 0/20 |
| Swara original | 600 | 263–600 | 13/20 | 13/20 |
| Swara changed | 600 | 46–111 | 0/20 | 0/20 |

The Swara original cap-hit IDs are **038, 012, 005, 042, 013, 004, 036, 022, 033, 023, 026, 040, 011**. Examples end at `यदि आप चाहें तो मैं आपकी बह` (005), `ऊपर बताए गए किसी` (004), and `## 3. कब हाथ धोना` (040). Exact cap usage plus visibly unfinished output strongly suggests length truncation. However, the client only checks that *some* `finish_reason` arrived and discards its value. The archive cannot prove `finish_reason=length` or split hidden reasoning from visible output. Incomplete-ending labels are reviewer annotations; cap counts are deterministic.

The **changed Swara replies are complete and well below the generation limit**. Their omissions arose while following a two-short-sentence instruction, not from an observed hard cutoff. Original truncation contaminates the comparison but does not explain away those omissions. There is no recorded cap-hit or visible-cutoff evidence for Samudra; unrecorded server behavior cannot be ruled out.

## Samudra: judge errors and genuine differences coexist

Conservative assistant classification of the paired texts: **3 likely false negatives**, **4 borderline comparisons**, **12 supported differences**, and **1 passed pair that nevertheless omits a policy precaution**. These are diagnostic categories, not an adjusted score. A supported difference can be an improvement, an omission, an added unsupported assertion, or a change of next action; it does not necessarily mean deterioration.

Clear judge problems:

- **020:** original says Padava supplies 3 GB/day and asks if more help is needed. Changed says the same and offers further help. The judge claims that the help offer was added.
- **023 and 011:** both answers ask the bill month and charge category. The judge quotes `విగ్రహం`, a word absent from both replies. Original actually uses `ఖర్చు విభాగానికి` (cost category). Changed uses charge terminology and examples. These are strong candidates for false negatives.
- **012:** the judge says changed added “data affected,” but original already asks whether internet is affected. Location examples differ, so this remains borderline rather than an automatic pass.
- **006:** the reason reverses the direction of the change. It is the **changed** answer that asserts benefits reset.

Clear response defects that judge errors do not excuse:

- **026:** the changed answer abandons the requested next network step and asserts Deevi is **1 GB/day**. Both system prompts and archived conversation say **4 GB/day**. This is a factual error, with no truncation signal.
- **006:** original says to check remaining benefits and terms; changed claims days, data and messages reset to the new plan. The system says to check the account, not that reset behavior is guaranteed.
- **033:** original identifies the **data-roaming setting**; changed discusses destination and network coverage without answering the requested setting question.
- **025**, the only pass, drops the original precaution to check remaining benefits and terms. That omission is material under the existing missing-facts instruction and policy, although the judge passes it.

Failures that do **not** establish meaning degradation include **036/040**, where changed adds the policy-supported international-roaming exclusion; and **042/022/037**, where changed asks for transaction time/status as policy requires, replacing less appropriate or invented baseline billing detail. For 022, original introduces an example INR 500 recharge and June 2026; the supplied catalogue contains no monetary prices.

## Swara: aggressive compression, unsupported baselines, unreliable reasons

All **20 pairs have identifiable content differences** under the existing strict equivalence rule. The appended instruction asks for at most two short sentences, while the retained Hindi system says to explain at length. The changed answers favor brevity, frequently replacing procedural detail with a follow-up question. This is an instruction tension and a plausible contributor, not a separately measured causal effect.

Examples with user-relevant loss or unsupported additions:

- **005:** changed omits the original explicit answer that the sister may participate, despite that being part of the user question.
- **034:** changed asks again whether voice information is wanted, dropping the original explanation of how to obtain it.
- **006:** changed newly requires the sister to bring an identity card. That requirement is absent from original and from supplied company context.
- **012:** changed newly offers medicine delivery, unsupported by the supplied prompt. Neither answer clearly answers whether the center action was performed.
- **020:** changed offers to book the appointment, although no booking capability was supplied to generation.

The original is **not a trustworthy reference answer**. For example, 026 guarantees ramps and lifts; 013/022/037 invent named websites, phone numbers and app features. None is supplied in the short system prompt or last user message. Archived prior turns instead ask users to confirm availability with the center. In 038 and 022, original interprets “large letters” as Latin **ALL CAPS**; 038's preceding user explicitly says small letters are hard to read. That is an accessibility-context mistake, not useful detail that a good shorter answer necessarily must preserve. This diagnosis makes no claim that the generated contact details are real or safe to use.

The final judge batch (**023, 026, 040, 011, 025**) contains garbled self-referential reasons and unsupported quoted propositions. In **040**, it says original describes center facilities and changed assumes none: original cuts off before a facility section, and changed makes no such denial. In **011**, changed explicitly offers an audio guide, contradicting the reason's “assumes no audio” wording. In **036**, changed retains soap/water and 20 seconds; the reason misleadingly describes a replacement by sanitizer. These flawed reasons warrant review, but concrete omissions still support non-equivalence in those pairs.

## Shared experimental limitations

`fix_experiment()` selects the last user turn of each sampled chat and sends only that text with the system prompt. It does not replay prior user/assistant turns. Requests such as “Did you do this at the center?” therefore lose the preceding explanation of what the bot can do. The archived snapshot shows the missing context, but it was not model input. Both arms are affected; this is a confound, not proof the tested lever caused every error.

Both arms used the same hosted **stand-in** model within each company, not the deployed model. Prompt language/length or the answer-cap instruction changes generation; the comparison does not isolate language-specific model accuracy. The judge then compares one generated response with another without grounding either against policy. Human/native-language review remains pending. No defensible corrected pass rate can be inferred merely by subtracting suspected judge mistakes.

## Disposition and reproducibility

Keep **1/20** and **0/20**, the failed-quality status, and the absence of a recommended top fix unchanged. Preserve the truncation limitation and questionable reasons alongside those outcomes. This audit proposes no contract amendment, threshold relaxation, prompt change, token-budget change, or retroactive rejudgment. Capturing finish reasons, restoring conversation context, or calibrating the judge would be separate follow-up work.

Evidence:

- `agent_v2_world_events.jsonl`: authenticated World Model archive.
- Samudra experiment `evt_6d086ad6d37fbd265c477208`, judge `evt_319936ae28eb8b67fc88e2f9`, snapshot `evt_06e4529f2c545beb2825b6f2`.
- Swara experiment `evt_f6d6d492285ad90573888e15`, judge `evt_20cddfb338e7e7661a4fed08`, snapshot `evt_18adc2fe2fa4d1a12e800eac`.
- `agent_v2_quality_diagnosis.jsonl`: complete paired texts, original verdicts/reasons, usage, cap flags, review annotations and provenance. It does not modify the original evidence or native-review queue.
- `scripts/check_quality_diagnosis.py`: verifies event hashes, exact copied pairs/verdicts, coverage, original scores, usage-derived cap flags and aggregate counts. It **does not validate semantic annotations**.

Validation commands and results are recorded in `agent_v2_quality_diagnosis_validation.jsonl`.

## Every paired reply reviewed
These are assistant diagnostic annotations, not replacement verdicts. The JSONL contains every full user message, both replies, usage, original judge verdict, provenance and analysis. Native-speaker sign-off remains pending.

### Samudra

**samudra-038** — borderline; judge reason: overstrict.

Original verdict: `false`. Reason: changed references 'Network situation' and specific details not in original

Both ask location and when calls stopped. Changed adds a network-status explanation; no clear loss of the requested next step. Neither explicitly names the technical team as the archived history does.

**samudra-012** — borderline; judge reason: incorrect reason.

Original verdict: `false`. Reason: changed added 'data affected' and rephrased location request

Original already asks whether internet is affected; changed asks whether data is affected. The judge invents that addition. Location examples do change from city/area to apartment/home. Both fail to answer whether the bot performed the action.

**samudra-047** — borderline; judge reason: partly supported.

Original verdict: `false`. Reason: changed rephrased data limit and added plan activation question

Both state Sagaram is 5 GB/day. Changed asks whether to activate, whereas original asks whether the information was seen. Different conversational direction, not loss of the numerical fact.

**samudra-005** — supported difference; judge reason: incorrect reason.

Original verdict: `false`. Reason: changed altered troubleshooting steps and added official contact instruction

Changed drops secure identity verification and the explicit statement that this bot cannot block or verify. Judge says official contact was added, but original already gives it. Both give questionable off-then-on SIM inspection wording; this is not solely a changed-answer defect.

**samudra-020** — likely false negative; judge reason: incorrect reason.

Original verdict: `false`. Reason: changed rephrased data limit and added offer for more help

Both state Padava is 3 GB/day and offer further help. The reason claims the help offer was added, although original already says it. Transliteration/spelling and wording differ without a meaningful factual change.

**samudra-042** — supported difference; judge reason: vague.

Original verdict: `false`. Reason: changed alters facts and context from original

Original requests bill month and service name; changed requests recharge date/time and payment status. Changed is closer to the system instruction for a missing recharge receipt. Non-equivalence does not establish deterioration.

**samudra-002** — supported difference; judge reason: vague.

Original verdict: `false`. Reason: changed differs from original instructions and process

Both route to official support and identity verification. Changed adds temporary blocking and SIM shipment, while omitting the original explicit inability to issue a SIM in this chat. These are substantive procedural differences.

**samudra-013** — supported difference; judge reason: vague.

Original verdict: `false`. Reason: changed alters required details and context from original

Original asks payment month/amount and payment-history status; changed asks plan/month, payment status and charge details. Actual detail substitution, with neither fully preserving the system request for transaction time/displayed status.

**samudra-034** — borderline; judge reason: overstrict.

Original verdict: `false`. Reason: changed omits key requirements and process details from original

Both direct the user to official support for identity verification. Changed omits portal/customer-support alternatives and the redundant request checklist. Whether those are material facts is debatable; no specific policy contradiction is shown.

**samudra-004** — supported difference; judge reason: vague.

Original verdict: `false`. Reason: changed alters facts and intent from original

Both preserve Ala 1 GB/day. Changed replaces the original account-check instruction about action completion with an activation question. This is an actual change of next action, not numerical loss.

**samudra-036** — supported difference; judge reason: incorrect reason.

Original verdict: `false`. Reason: one checks official availability, other confirms blocked

Original asks destination and official availability; changed states international roaming is not included and asks for an official availability check. The judge says blocked, which neither reply says. The added exclusion is explicitly supported by both system prompts.

**samudra-006** — supported difference; judge reason: reversed direction.

Original verdict: `false`. Reason: benefit reset details vs just plan change info

Original says check remaining benefits and terms before changing. Changed instead asserts days/data/messages reset to the new plan. Judge reverses which answer contains reset details. The reset assertion is unsupported by the system policy, which says to check the account.

**samudra-022** — supported difference; judge reason: incorrect reason.

Original verdict: `false`. Reason: specific error message vs status check instruction

Original invents an example June 2026 recharge of INR 500; changed asks transaction time/current status via official support, matching the system policy. Judge describes an original error message, absent from original. Real difference, with changed better grounded.

**samudra-033** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: specific setting vs general country/network check

Original names the data-roaming setting, answering the user. Changed only asks destination/network coverage and loses the requested setting. A clear omission unrelated to truncation.

**samudra-037** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: detailed details vs just status info

Original asks month/date/amount/payment method and invents June 2026 as an example. Changed asks transaction time/status through official support, closer to the system policy. Not equivalent, but loss of original detail is not automatically loss of valid information.

**samudra-023** — likely false negative; judge reason: hallucinated quote.

Original verdict: `false`. Reason: Changed 'విగ్రహం' to 'ఛార్జ్' altering the factual context from section to charge.

Both ask bill month and charge category; changed gives charge examples. Judge quotes విగ్రహం, absent from both replies. Original actually says ఖర్చు విభాగానికి (cost category). No meaningful factual contradiction is identified.

**samudra-026** — supported difference; judge reason: supported but incomplete.

Original verdict: `false`. Reason: Changed content entirely from connection troubleshooting steps to daily data limit inquiry.

Original gives airplane mode for 10 seconds and further network checks. Changed switches to a daily-allowance question and asserts Deevi is 1 GB/day, contradicting 4 GB/day in both systems and archived history. The judge catches the topic switch but misses the numeric error.

**samudra-040** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed from checking international roaming availability to stating it is unavailable and requiring official channel check.

Original asks destination and availability. Changed explicitly excludes international roaming and requests separate permission/availability checks. Those added facts match the system policy; this failure is not evidence the English prompt worsened factuality.

**samudra-011** — likely false negative; judge reason: hallucinated quote.

Original verdict: `false`. Reason: Changed 'విగ్రహం' to 'ఛార్జ్' and added base plan/extra services categories, altering the factual context.

Both ask bill month and charge category and offer help. Changed gives base-plan/additional-service examples matching policy. Judge again quotes విగ్రహం, absent from either reply; original says ఖర్చు విభాగానికి.

**samudra-025** — passed with omission; judge reason: missed omission.

Original verdict: `true`. Reason: Same facts: both confirm plan change is possible before expiry, with login required in changed version.

Both say a pre-expiry plan change is possible and describe account navigation. Changed omits checking remaining benefits and terms before changing, which original and system explicitly require. The sole pass is questionable under the same missing-facts rule.

### Swara

**swara-038** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: changed asks about method (email/form), original details request process for CAPS copies

Changed preserves a usable request sentence but omits phone/in-person routes and delivery/fee/time details. Original misreads large print as Latin ALL CAPS; archived history explicitly concerns difficulty reading small letters. Removing that mistaken expansion is not necessarily lost quality.

**swara-012** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: changed offers online consultation/medicine delivery, original explains remote care platform features

Changed newly claims medicine delivery and online consultation; original describes an elaborate remote-care platform. Neither answers whether work was done at the center. The delivery claim is unsupported by the supplied system/last user turn.

**swara-047** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: changed asks about morning meeting time, original confirms both online/call scheduling available at center

Changed asks date/time but omits contact channels, confirmation and rescheduling steps. Original also invents a helpline and center capabilities. Both avoid clearly saying whether the bot has actually booked anything.

**swara-005** — supported difference; judge reason: supported but incomplete.

Original verdict: `false`. Reason: changed claims water prevents shortage and aids digestion, original details hydration amounts and sources

Changed gives a short hydration statement and asks about quantity, dropping the explicit yes to sister participation in original. This loses a user-requested point, independently of the original ending being cut off. Original contains its own questionable health wording; it is not a validated reference.

**swara-020** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: changed asks to book time, original provides sister-assisted dialogue and process steps

Changed drops sister-assisted process/confirmation steps and offers to book for the user. No booking capability was supplied. Original contains a fuller request script but is itself unsupported on operational details.

**swara-042** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed text removes location details and specific sources; only generic tips and remote features kept.

Changed keeps an app source, sleep tracking and smart alarm, omitting other sources and remote options. Original fabricates URLs, app sections and integrations absent from the prompt. Difference is clear; truth of omitted service claims is not established.

**swara-002** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed text shortens family member guidance and replaces scheduling steps with a generic tool suggestion.

Changed preserves family accompaniment and a generic scheduling route, but loses call/chat, slot, confirmation and reminder steps. This is substantial compression; original service details are not grounded in supplied company facts.

**swara-013** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed text replaces detailed step-by-step scheduling with a single app click instruction.

Changed keeps an app information source and scheduling action, dropping alternatives, reminders and follow-up notes; even the app section names differ. Original exact phone/URL/features are unsupported by the generation input.

**swara-034** — supported difference; judge reason: misleading.

Original verdict: `false`. Reason: Changed text condenses the family member and voice info into a yes/no question pair.

Changed keeps permission to bring family but asks again whether voice information is wanted, instead of explaining how to obtain it. The judge calls this a yes/no question pair, though the first sentence is an affirmative statement. Omission is still real.

**swara-004** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed text replaces the multi-method time-request process with a single app option and asks a follow-up question.

Changed reduces phone/app/email routes to an asserted audio-appointment feature. It omits registration and other steps and does not answer whether an action was performed. That named feature is unsupported by supplied context.

**swara-036** — supported difference; judge reason: misleading.

Original verdict: `false`. Reason: Changed message promotes sanitizer; original teaches handwashing steps

Changed retains soap/water and 20 seconds, then adds sanitizer. It does not simply replace handwashing with sanitizer as the reason implies. It omits wash/dry steps, occasions and center-facility claims; the latter are ungrounded in original.

**swara-006** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed restricts sister to ID requirement; original allows her to join call/app freely

Changed newly requires the sister to bring an identity card. Original permits participation and provides rescheduling/confirmation steps. This added requirement is unsupported, and omitted rescheduling details are substantive.

**swara-022** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed truncates sources and omits large‑caps request steps

Changed keeps an app route and large-print request but loses phone/text/form/email routes and timelines. Original confuses large print with ALL CAPS and fabricates numbers/addresses/24-48 hour service. The word truncates in the reason describes condensation; changed is complete and below cap.

**swara-033** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed replaces morning time guidance with calendar slot instruction

Changed retains soap and 20 seconds but drops detailed wash/dry/when steps. It substitutes a 10-15 minute call slot for original morning reminders. Real content difference; original itself confuses a conversation appointment with a daily hygiene reminder.

**swara-037** — supported difference; judge reason: supported.

Original verdict: `false`. Reason: Changed narrows sleep info to app section; original lists multiple sources

Changed narrows sources to the app and asks about the sister logging in; original permits shared-device/phone/clinic participation. It loses channels and participation options, while original exact service details are unsupported.

**swara-023** — supported difference; judge reason: unreliable reason.

Original verdict: `false`. Reason: changed: user queries remote access to habit info, original details login steps, contradicts 'missing remote steps'

Changed offers form/helpline and a link, omitting original login/contact/service details. The reason repeats the user question and quotes a nonexistent missing remote steps assertion, rather than identifying a concrete pair contradiction. Difference remains independently visible.

**swara-026** — supported difference; judge reason: unreliable reason.

Original verdict: `false`. Reason: changed: user asks about stairs access and remote parts, original details entrance and remote processes, contradicts 'remote process details'

Original guarantees ramps/lifts and lists remote booking, consultation, documents, payment and follow-up. Changed says access can be requested and asks which remote stage. That is different and more cautious about unverified facilities. The judge quotes a nonexistent remote process details assertion.

**swara-040** — supported difference; judge reason: hallucinated claim.

Original verdict: `false`. Reason: changed: user asks about hand washing done at center, original explains steps and center facility, contradicts 'changed assumes no facility'

Changed compresses handwashing to a brief rule and sanitizer, omitting detailed steps. Judge says original explains a center facility and changed assumes no facility: original cuts off before such a section and changed asserts no such absence. Non-equivalence is real, but the reason is not grounded in the texts.

**swara-011** — supported difference; judge reason: hallucinated claim.

Original verdict: `false`. Reason: changed: user asks how to request walking habit info audio, original details steps to request audio, contradicts 'changed assumes no audio'

Original explains requesting and receiving audio, with a service workflow; changed asserts an app audio download and offers a link. Judge implies changed assumes no audio, directly contradicted by the changed audio-guide sentence. The delivery method and omitted process still differ.

**swara-025** — supported difference; judge reason: unreliable reason.

Original verdict: `false`. Reason: changed: user asks about remote parts of rescheduling, original details all remote steps, contradicts 'changed assumes only portal'

Changed preserves app/portal rescheduling and email/SMS confirmation but omits phone/email contact, proposal/acceptance and in-person distinction. It says portal OR mobile app, not only portal as the quoted judge phrase suggests. Failure remains defensible for omissions.
