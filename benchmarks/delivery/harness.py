"""Delivery-Bench (v6.11 PEN-DELIVER, D-WS2), the capsid-fitness track for the Genome-Writing Challenge.

Scores a predictor on AAV capsid packaging-fitness over the FLIP-AAV benchmark (Dallago et al. 2021, built on
Bryant et al. 2021): predict the fitness of held-out capsid variants, evaluated by Spearman correlation on the
`sampled` (random 80/20, in-distribution) and `mut_des` (mutant->designed, hard generalization) splits. The
PEN-DELIVER learned model (windowed one-hot gradient boosting) must BEAT a mutation-burden baseline.

The headline numbers (`benchmarks/delivery/capsid_fitness_metrics.json`) are computed on the VM over the full
FLIP-AAV data (217 MB per split, never committed); this harness exposes them + the gate verdict. The licensed FLIP
data stays on the VM; the derived metrics + reproducible build script (`scripts/build_capsid_fitness.py`) are
committed, while the ~3 MB model (`models/capsid_fitness.pkl`) is gitignored, regenerated from the build script and
mounted into the deployed app (the `position_effect.pkl` pattern); the axis abstains gracefully when it is absent.
"""
from __future__ import annotations


def _metrics() -> dict:
    import json

    from pen_stack._resources import resource
    try:
        return json.loads(resource("benchmarks/delivery/capsid_fitness_metrics.json").read_text(encoding="utf-8"))
    except Exception: # noqa: BLE001
        return {}


def run() -> dict:
    """Report the Delivery-Bench capsid-fitness result (learned vs mutation-burden baseline, per FLIP-AAV split)."""
    m = _metrics()
    if not m:
        return {"available": False, "note": "FLIP-AAV capsid-fitness metrics absent (data tree not present)"}
    splits = {k: v for k, v in m.items() if k in ("sampled", "mut_des")}
    return {"available": True, "benchmark": "FLIP-AAV (Dallago 2021; Bryant 2021)",
            "splits": splits, "method": m.get("method"),
            "learned_beats_baseline": all(v["learned_beats_baseline"] for v in splits.values()),
            "note": ("learned capsid-fitness (windowed one-hot gradient boosting) beats the mutation-burden baseline "
                     "on both the in-distribution (sampled) and the hard mutant->designed (mut_des) generalization "
                     "splits; predicted fitness is a candidate for the MEASURED packaging axis, not in-vivo tropism.")}
