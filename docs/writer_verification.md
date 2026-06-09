# Writer verification (v4.0, WS-WV) — the honest "better pen"

PEN-STACK does **not** invent writer enzymes de-novo. The earlier `pen-assemble` direction produced **0
validatable de-novo writers** and could not be checked computationally. v4.0 builds the honest alternative:
**score and critique** proposed or variant writers against measured data — never assert novel function.

## WV1 — variant scoring (DMS- + structure-grounded)

`pen_stack.atlas.writer_verify.score_variants(variants)` returns, per variant, a **calibrated activity score**
in [0, 1] with an interval and a scope flag:

- A variant present in the **Perry-2025 ISCro4 deep mutational scan** is scored from its *measured* activity
  Z-score → `claimable=True`, finite interval.
- A variant **out of the DMS distribution** → `extrapolating=True`, `claimable=False` — a plausibility screen
  only, **no activity claim**.

`blind_recovery()` is the deterministic retrospective criterion: ranking the documented panel, the known
enhancers **N322P / H50K / R278M** land on top, above the measured-worse controls. `real_dms_recovery()`
reports the same against the full Perry DMS when it is present (on the VM). This is a *catalogue* feature that
recovers known enhancers — **not** a blind sequence-only predictor, and stated as such.

## WV2 — critique, not invention

`critique_candidate(seq, ...)` takes a **generated** candidate writer (e.g. from `oracles.protein_design`,
which only ever returns `candidate` outputs) and critiques it:

| Check | Source |
|---|---|
| folds? | structure oracle (`oracles.structure.consistency`) — deferred → flagged, never asserted |
| plausible active site? | retains conserved core residues (heuristic) |
| deliverable form? | the rule-grounded verifier (delivery rules) |
| reachable target? | the rule-grounded verifier (reachability rules) |

It returns `pass`/flags + reasons, and **always** `no_claim=True`, `claimable=False`. A generated writer is
never returned as "a working new pen." The verifier surfaces this as `Verdict.writer_critique` (a scope flag,
never a confidence): the legality of the write *plan* and the activity *claim* for the candidate are distinct
axes — a legal plan does not make an unverified candidate claimable.

## Scope & honesty

- Deep DMS exists for **few** enzymes (bridge recombinases); elsewhere WV1 is a labelled plausibility screen.
- Generative designs are **proposals**; they are scored/critiqued, never asserted active.
- Structure verification is deferred without an AF3/Boltz/Chai/Protenix backend or a committed cache entry —
  the candidate is then explicitly *fold-unverified*, not assumed to fold.

See `docs/oracles.md` (the mesh), `prereg/ws_wv.yaml`, and `pen_stack/atlas/writer_verify.py`.
