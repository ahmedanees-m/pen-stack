# The closed loop

PEN-STACK integrates every prior cycle into one continual **design→build→test→learn** loop, with humans/lab
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

1. **generate**: safe + legal + calibrated + immune-profiled candidates (the verifier-as-discriminator
   discards hazardous/illegal proposals);
2. **decide**: `select_batch` picks a diverse, informative batch (EIG + immune-VOI);
3. **safety + build**: `export_protocol` is **safety-gated** (a flagged design is blocked);
4. **test**: `run_simulated` (sim-lab) or a real lab at the same interface;
5. **ingest**: results enter as candidate evidence, admitted only through the gate;
6. **drift**: predicted vs observed;
7. **learn**: `continual_update` recalibrates, versioned + reversible.

The loop **pauses for the approver at safety, build, and belief-admission**; it is not autonomous.

## Drift detection (`pen_stack/loop/drift.py`)

`detect_drift(designs, results)` compares the twin's predictions against observed readouts. Growing
miscalibration → `severity: "high"` → `action: "inflate_intervals"`, widening uncertainty rather than over-trusting a
stale model. Covers calibration/residual shift, not every failure mode.

## Continual learning (`pen_stack/loop/continual.py`)

`continual_update(admitted_results, drift=…, approver=…, prev_version=…)` recalibrates the trust layer, the
twin, and the immune proxies **on admitted outcomes only**. Every update is **versioned** (evidence digest)
and **reversible** (`rollback_to` the prior version), attributable to the approver. High drift widens intervals.
An admitted immune measurement **with a CI** can move an axis proxy → outcome-validated. This is
**recalibration, not foundation-model retraining**.

## Convergence demonstration

`loop_converges_faster_than_random` reports, retrospectively and with a bootstrap CI, whether the loop's active
Learn stage reaches a target model quality in fewer rounds than random selection (validated). It is
reported either way; the demonstration is retrospective/simulated.

## Scope

The loop is **Level 3**: closed, but with humans/lab in control at every gate, **not autonomous**. It runs in
silico via the sim-lab (a real lab attaches at the same interface); continual learning recalibrates rather than
retrains; drift detection covers calibration/residual shift, not all failures; immune-proxy graduation requires an
admitted measurement with a CI. See [Autonomy levels](autonomy.md).

## The self-driving-lab engine

This engine extends the loop into a genome-writing-specific, biosecurity-gated self-driving-lab engine: a cloud-lab
connector, an SDL-brain benchmark, and a validation-campaign engine. It consumes the WriteSpec and pairs
with the biosecurity gate.

- **Cloud-lab connector** (`pen_stack/build/cloudlab.py`). `submit_gated` bridges the build interface to a cloud
  lab. The biosecurity gate runs BEFORE submission: a flagged or illegal design makes `export_protocol` raise, so
  no protocol is emitted (a ricin design is refused), and `submit_gated` returns a structured refusal. A cleared
  design returns a mock / dry-run job receipt (a real wet run needs a partner + budget). `ingest_readout` admits a
  returned readout only through an explicit human-in-control gate (Level 3).
- **SDL-brain benchmark** (`pen_stack/active/brains.py`). Benchmarks the EIG/VOI designer against the public SDL
  optimizers BayBE (Apache-2.0) and Atlas on a shared retrospective acquisition task, reported verbatim with both
  cited. The designer shows a positive mean information-gain advantage over random whose bootstrap CI is
  rep-sensitive (it includes 0 at higher rep counts), reported as not-CI-significant rather than hidden; where
  BayBE is installed a real head-to-head runs.
- **Validation-campaign engine** (`pen_stack/active/campaign.py`). Points active learning at the
  expression axis: it orders the candidate (cassette x locus x cell type) measurements by expected
  information gain, names the `validate.calibrate_axis` gate they would flip, and emits an executable,
  cloud-lab-submittable spec (`out/expression_validation_campaign.md`). The campaign measures independent data,
  never the model's own outputs; the experiments are candidates and the wet run is the standing bottleneck.

Surfaces: REST `GET /api/campaign`, `POST /api/cloudlab`, `GET /api/brains`; MCP `validation_campaign`,
`cloudlab_submit`. Reported by `benchmarks/loop/`.
