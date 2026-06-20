# The generative designer (v5.8)

From v5.8, PEN-STACK does not only *score* a design you give it; it *generates* candidate end-to-end writing
systems and returns the **Pareto frontier** of real tradeoffs, with every candidate passing safety, legality,
and calibration or being discarded. Generation proposes; `verify()` disposes.

## Verifier-as-discriminator (`pen_stack/design/generate.py`)

```python
from pen_stack.design import generate_designs
survivors = generate_designs({"gene": "AAVS1", "intent": "safe_harbour_insertion",
                              "cargo_bp": 3000, "cell_type": "k562"})
```

Each candidate is run through the v3.3 `verify()`, now **safety-gated (v5.7)**, legality-checked (v3.3),
calibrated (v3.2), and immune-profiled (v5.6). A candidate **survives only if it is legal AND its safety
decision is `clear`/`flag`**; hazardous (`refuse`/`escalate`) and illegal candidates are **discarded, never
returned as claims**. Survivors carry:

- `confidence` + `interval`: calibrated (or an explicit `None` abstention),
- `immune_profile`: the v5.6 per-axis vector (`collapsed_score` stays `None`),
- `safety_decision`, `scope_flags`,
- `output_kind: "candidate"`: never asserted to work.

This generalises the v4.0 `as_claim()` guard from single oracle outputs to whole designs. A novel writer
sequence in a candidate routes to v4.0 writer-verification (critiqued, never claimed).

Pass an explicit `candidates=[...]` pool to discriminate a known set (atlas-independent); otherwise candidates
are enumerated by `candidate_space(goal)`: the validated Phase-3 planner (`plan_write`) crossed with every
compatible delivery vehicle.

## Pareto frontier with a grounded immune-risk axis (`pen_stack/design/pareto.py`)

```python
from pen_stack.design import pareto_front
front = pareto_front(survivors)        # non-dominated set
```

Axes (higher is better on each): `efficiency` (writer activity), `durability` (TRIP model), `safety`
(genotoxicity-risk), `deliverability` (capacity headroom), **`neg_immune_risk`**, `neg_cost`.

`neg_immune_risk` is **grounded by the v5.6 profile, not a placeholder**: it is the **worst-case per-axis
in-scope score** (lower score = higher risk) with the largest per-axis uncertainty carried as a **band**. The
profile is never collapsed into one confident number, and the in-vivo magnitude stays scope-flagged
(`in_vivo_magnitude_unknown`). Each frontier design exposes `neg_immune_risk_detail` (value + band + axes used +
flag); the per-axis profile remains the source of truth.

## Live orchestration (`pen_stack/agent/orchestrator_live.py`)

```python
from pen_stack.agent.orchestrator_live import orchestrate
run = orchestrate(goal)                # plan -> generate -> oracle critique -> verify -> refine
```

The agent picks *which* oracle to call; the *number* always comes from the oracle (cache-first, version-pinned,
**replayable**; replay is the CI default). A seed-locked replay reproduces the trace exactly. No stage
fabricates a value.

## Scope

Generation explores within the oracles' validity and the rules' legality; novelty is bounded and **never
asserted to work**. The immune-risk Pareto axis is a worst-case **screen** over per-axis proxies; the per-axis
profile (with its validation labels) is authoritative, and in-vivo magnitude remains a known-unknown.
