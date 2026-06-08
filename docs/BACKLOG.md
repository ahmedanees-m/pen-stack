# PEN-STACK — Backlog (out of scope for the current cycle)

New ideas land here rather than expanding an in-flight cycle (per the v3.2 plan's scope discipline).

## WS-OPT2 — Opentrons protocol export (deferred)

Generate a reviewable OT-2 / Flex liquid-handling protocol artifact from a finalized write plan (cloning /
assembly / delivery steps), labeled **"generated, requires human review, never auto-run."**

**Status: deferred (not built).** It edges toward the wet-lab boundary the program intentionally avoids
(PEN-STACK is decision-support, not an instrument controller). Include only if explicitly requested. If built,
it must: (a) emit a static, human-readable protocol (no execution hooks); (b) carry the review/no-auto-run
disclaimer prominently; (c) stay behind an optional extra so the core install never pulls an instrument SDK.

## Other parked ideas

- Scaling the validated gold sets further (more CAST/PASTE/integrase writes; external leaderboard submissions)
  to narrow the wide conformal intervals — ongoing, not a blocker.
- Conditional (per-query) conformal coverage beyond the marginal guarantee — a research direction, not a
  committed deliverable.
