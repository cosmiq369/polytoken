# PolyToken investigation workspace

The audience is an engineer or product lead investigating an AI workload's cost,
quality and speed. The first screen answers: what is happening, why, what comes
next, and which findings are safe to use. Trace detail and resource counters are
available without competing with that answer.

The October 25 redesign replaces the monochromatic service diagram with an
investigation desk. A prominent briefing explains the current work and next
checkpoint. A nine-stage path highlights the active stage and opens its trace
with keyboard focus. Stages can repeat: “Recorded” means a stage appeared in the
log, not that its business hypothesis passed. The stage follows the latest
step_started event, so old experiment progress cannot mask a later quality or
speed check. Replaying an archive never rewrites its saved completion status.

Checked findings sit beside the path. Service lanes group orchestration, data,
model generation, memory and verification. Detailed spans, resource budgets and
raw observations follow below. Overview, Billing, Quality, Evidence and Token
strip retain their report, accounting, comparison and receipt workflows.

## Visual language

The logo's cyan and gold are confined to the mark. The interface uses neutral
surfaces and a separate semantic palette, with labels accompanying every state:

| Role | Light | Dark |
| --- | --- | --- |
| Canvas | #f3f4f6 | #15171c |
| Surface | #ffffff | #202329 |
| Text | #20242d | #f1f2f5 |
| Secondary text | #586170 | #b5bdc9 |
| Active / selection | #244ec7 | #a5bbff |
| Testing / caution | #865200 | #f4c466 |
| Verified | #14633f | #91dbaf |
| Model / memory | #6842a6 | #cdb2fa |
| Failure | #b52f3f | #ffabb5 |

System sans carries the hierarchy, with monospace limited to identifiers,
measurements and telemetry. Local fonts and existing Indic fallback keep startup
offline. Theme preference persists. No CDN, framework, dependency or build step
was added.

## Navigation and accessibility

A viewport grid keeps the workspace rail, run controls and view tabs in place.
The main content and recent-run history scroll independently. Below 900px the
rail becomes a persistent top navigation; the stage path becomes a horizontal
strip that brings the current stage into view. Service groups wrap as space
shrinks. The event console has a bounded height and its own scrolling area.

Native buttons, details, labels and a range input provide keyboard interaction.
Alt+R starts/re-runs, Alt+S stops, and Alt+1…8 selects views. Stage selection opens
and focuses the relevant trace summary. Focus outlines and reduced motion are
explicit. The briefing is announced politely; unchanged briefing markup is
preserved between events.

Acceptance checks cover both themes, all views, text contrast of at least 4.5:1
for tested UI text, navigation stability at 320–1280px, current-stage visibility,
keyboard focus, reduced motion and 640×475 CSS-pixel reflow (the space available
in a 1280×950 window at 200% browser zoom). These are defined checks, not a claim
of a complete accessibility certification or cross-browser audit.

## Evidence and replay

Replay follows recorded timestamps, including quiet gaps, at 1×, 4× or 16×.
Scrubbing rebuilds the same event reducer. Old logs have no physical call spans:
their observations disclose unavailable call timing. Checked findings in legacy
logs appear with the final report. No duration, intermediate finding or budget
ceiling is invented. The last-event age uses recorded time during replay.

Stop is cooperative: a bounded in-flight HTTP call may finish before the shared
cancellation guard prevents the next attempt or background job from starting.
