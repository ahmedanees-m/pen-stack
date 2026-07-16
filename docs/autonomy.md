# Autonomy levels: PEN-STACK stops at Level 3 (v5.12)

PEN-STACK's closed loop (v5.12) is a **Level-3** design→build→test→learn engine: closed, but with **humans/lab in
control at every gate**. This is the program's deliberate ceiling, not Level 5.

## The levels (for self-driving labs)

| Level | Description | PEN-STACK |
|---|---|---|
| 0 | Manual: a human does everything | (n/a) |
| 1 | Assisted: tools score/check, human decides each step | v3.3 verifier |
| 2 | Partial: the system proposes designs + experiments; human runs + decides | v5.8, v5.11 |
| **3** | **Closed loop with human control at every gate**: the system runs the full cycle, but pauses for human approval at safety, build, and belief-admission, and flags anomalies | **v5.12 (here)** |
| 4 | Supervised autonomy: runs many cycles with human oversight, escalating exceptions | not claimed |
| 5 | Full autonomy: no human in the loop | **not claimed; not a goal** |

## What "Level 3" means here (asserted criteria)

1. **Closed loop.** One command runs generate → predict → decide → safety → build → ingest → learn end-to-end
   (`run_loop`), in silico (sim-lab) or with a real lab at the same interface.
2. **Human in control at every gate.** The loop pauses for the `approver` at **safety** (export is refused for a
   flagged design), **build** (protocols are DRAFTs requiring human/lab review), and **belief-admission** (results
   enter the curated world-model only via the v4.5 gate with explicit approval).
3. **Anomaly flagging.** Drift between predictions and observations is detected and **widens uncertainty** rather
   than over-trusting a stale model. Continual updates are versioned and reversible.
4. **No fabrication.** Every number is tool-sourced; no stage invents a value.

## What PEN-STACK deliberately does NOT do

- It does **not** run experiments autonomously (protocols are drafts; a human/lab runs them).
- It does **not** auto-edit the curated world-model (admission requires human approval).
- It does **not** retrain the foundation models (continual learning is recalibration).
- It does **not** claim Level 4 or 5. The human is in the loop by design.

> Level 3 is a trustworthy ceiling: a closed, gated, drift-aware loop that a scientist drives, not an autonomous
> agent acting in the world. The convergence demonstration is retrospective/simulated, reported with CIs.
