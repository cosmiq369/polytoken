# PolyToken agent console

The audience is an Indian AI engineering team investigating its inference bill.
The screen's job is to make the agent's current work, evidence and stopping point
visible without asking the team to read an article.

The signature is a service circuit: planner → tools → federated data and model
services → evidence and checker. Activity and latency belong to actual spans.
The quieter trace beneath it is the detailed, keyboard-accessible alternative.

The initial concept used a large finding at the top. That repeated the static
ledger's weakness, so the final hierarchy puts run status and the circuit first.
Results live in Overview, Billing, Quality, Evidence and Token strip tabs.
Billing retains the measured composition, resend staircase, model comparison,
what-if controls and exact receipts from 05B.

Palette: midnight blue #101c2c, slate #192a40, mist #e8f0fa, steel #b1c2d6,
cyan #76d9ed and coral #ffabb1. Light mode uses snow #f3f6fa, white #ffffff,
ink #172a40, slate #475c72 and deep teal #075e73. Coral/deep red marks errors;
cyan/deep teal marks selected paths and verified evidence. Color is always
accompanied by a label or status. Theme selection is persistent in Settings.

System sans (Arial/Helvetica) is the 14px body and restrained 20px heading face;
Menlo/Consolas is the utility face for identifiers, figures, SQL and durations.
Local system fonts keep offline startup deterministic and support Indic fallback.
No CDN, framework, new dependency or build output is required.

Layout: a 200px investigation rail; a persistent run bar and tab row; a service
circuit over a split trace/findings workspace. On narrow screens the rail becomes
a compact top navigation and the map becomes a node grid. Panels scroll locally.
Keyboard: Alt+R starts/re-runs, Alt+S stops, Alt+1…8 selects run tabs.
Native buttons, details, labels and range input support keyboard navigation;
focus rings and reduced-motion handling are explicit.

Replay uses recorded timestamps, including long quiet gaps, at 1×, 4× or 16×.
Scrubbing rebuilds the same event reducer from the beginning. Old logs have no
physical call spans: their step/tool observations are labelled as legacy with
unknown latency, never presented as measured call durations. Checked findings
in legacy logs become available with the final report, not before the checker.
Stop is cooperative: a bounded in-flight HTTP call may finish, but the shared
cancellation guard prevents the next attempt and background job from starting.
