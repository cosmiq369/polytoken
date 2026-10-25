# Native Telugu review, Samudra fix "keep system instructions in English" (v3)

Reviewer: Mohan Chelluru, native Telugu speaker. Date: 25 Oct 2026. Source sheet: `logs/sample/native_review_samudra.md` (run `90571737-0cb7-4f20-91fd-e11bd19c62cd`, 10 pairs, seed 20261024, chosen without reference to judge outcome).

| # | Chat | Verdict | Reviewer's reason |
|---|---|---|---|
| 1 | samudra-042 | same meaning | |
| 2 | samudra-012 | different meaning | A asks for the area and start time to report the complaint; B apologises that it cannot help and only tells the customer to contact the support centre. Both point to support, but B declines directly. |
| 3 | samudra-005 | same meaning | |
| 4 | samudra-023 | different meaning | A asks follow-up questions to understand the issue; B says it cannot help and tells the customer to call support. |
| 5 | samudra-002 | same meaning | |
| 6 | samudra-006 | same meaning | |
| 7 | samudra-022 | same meaning | |
| 8 | samudra-033 | same meaning | |
| 9 | samudra-037 | same meaning | |
| 10 | samudra-025 | same meaning | |

Result: 8 same, 2 different, 0 unsure. Under the contract, any "different meaning" verdict blocks the fix, so the English-instructions fix is **rejected on native review**. Both differences show the same behaviour change: with English instructions the stand-in model declines and redirects instead of gathering details.
