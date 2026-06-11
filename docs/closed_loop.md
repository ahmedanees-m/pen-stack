# The closed loop (v5.12)

From v5.12, PEN-STACK integrates every prior cycle into one continual **design→build→test→learn** loop — humans/lab
in control at every gate, no fabrication, drift-aware. One command runs it end-to-end.

```python
from pen_stack.loop import run_loop
result = run_loop(goal, cell_state="k562", candidates=pool, rounds=5, approver="human")
result["autonomy_level"]      # 3
result["human_in_control"]    # True
result["history"]             # per-round: n, blocked, best_readout, drift, versioned update
```

## The DBTL orchestrator (`pen_stack/loop/cycle.py`)

Each round composes the whole stack:

1. **generate** (v5.8) — safe + legal + calibrated + immune-profiled candidates (the verifier-as-discriminator
   discards hazardous/illegal proposals);
2. **decide** (v5.10) — `select_batch` picks a diverse, informative batch (EIG + immune-VOI);
3. **safety + build** (v5.7 + v5.11) — `export_protocol` is **safety-gated** (a flagged design is blocked);
4. **test** (v5.11) — `run_simulated` (sim-lab) or a real lab at the same interface;
5. **ingest** (v4.5) — results enter as candidate evidence, admitted only through the gate;
6. **drift** (v5.12) — predicted vs observed;
7. **learn** (v5.12) — `continual_update` recalibrates, versioned + reversible.

The loop **pauses for the approver at safety, build, and belief-admission** — it is not autonomous.

## Drift detection (`pen_stack/loop/drift.py`)

`detect_drift(designs, results)` compares the twin's predictions against observed readouts. Growing
miscalibration → `severity: "high"` → `action: "inflate_intervals"` — widen uncertainty rather than over-trust a
stale model. Covers calibration/residual shift, not every failure mode.

## Continual learning (`pen_stack/loop/continual.py`)

`continual_update(admitted_results, drift=…, approver=…, prev_version=…)` recalibrates the trust layer, the v5.9
twin, and the v5.6 immune proxies **on admitted outcomes only**. Every update is **versioned** (evidence digest)
and **reversible** (`rollback_to` the prior version), attributable to the approver. High drift widens intervals.
An admitted immune measurement **with a CI** can move a v5.6 axis proxy → outcome-validated. This is
**recalibration, not foundation-model retraining**.

## Convergence demonstration

`loop_converges_faster_than_random` reports — retrospectively, with a bootstrap CI — whether the loop's active
Learn stage reaches a target model quality in fewer rounds than random selection (the v5.10 validation). It is
reported honestly either way; the demonstration is retrospective/simulated.

## Honest scope

The loop is **Level 3** — closed, but with humans/lab in control at every gate, **not autonomous**. It runs in
silico via the sim-lab (a real lab attaches at the same interface); continual learning recalibrates rather than
retrains; drift detection covers calibration/residual shift, not all failures; immune-proxy graduation requires an
admitted measurement with a CI. See [Autonomy levels](autonomy.md).
