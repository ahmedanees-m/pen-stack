"""Writer-Efficiency Bench, the cross-family integration-efficiency track for the Genome-Writing Challenge
(v6.8 PEN-WRITER, C-WS1).

The first curated, leakage-controlled benchmark for predicting genome-WRITER integration efficiency. Given
`(family, write-type, cargo, locus, cell-type, variant)`, predict the integration **efficiency (%)**, scored
on **held-out family** and **held-out locus** folds (the two ways a predictor must generalise). The label is the
**measured published efficiency** (real, DOI + verbatim quote per row, NON-circular), not a submitter claim.

Two evaluation axes (both leakage-controlled, leave-one-group-out):
  * `held_out_family`, train on 3 families, predict the 4th (cross-family transfer; the hard axis).
  * `held_out_locus`, train on all-but-one specific locus, predict the held-out locus.

Baselines: the KB family-mean prior (what the curated KB ranking implies) vs the PEN-WRITER learned predictor.
Result (v6.8): the learned model beats the KB baseline on held-out LOCUS (CI excludes 0) but NOT on
held-out FAMILY at this N (4 families), so the KB ranking is retained as primary and the dataset + bench are the
standalone contribution. Sealed + SHA-locked (split.json + the dataset parquet).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pen_stack.atlas.writer_efficiency import human_cell

_HERE = Path(__file__).resolve().parent


def spec() -> dict:
    return json.loads((_HERE / "split.json").read_text(encoding="utf-8"))


def dataset(strict: bool | None = None):
    """The benchmark dataset (human-cell). `strict` (default from split.json) keeps only pmc_verbatim+abstract."""
    s = spec()
    strict = s.get("strict_source", False) if strict is None else strict
    return human_cell(strict=strict).reset_index(drop=True)


def baseline_leaderboard() -> dict:
    """Reproduce the baseline leaderboard (KB family-mean vs PEN-WRITER learned) on both held-out axes."""
    from pen_stack.atlas.writer_predict import evaluate
    rep = evaluate(dataset())
    board = {}
    for axis in ("held_out_family", "held_out_locus"):
        a = rep.get(axis, {})
        if not a.get("n"):
            continue
        board[axis] = {
            "n": a["n"],
            "KB_family_mean": {"mae": round(a["mae_baseline_family_mean"], 2),
                               "spearman": round(a["spearman_baseline"], 3)},
            "PEN_WRITER_learned": {"mae": round(a["mae_model"], 2), "spearman": round(a["spearman_model"], 3)},
            "mae_reduction_ci95": a["delta"]["ci95"],
            "learned_beats_baseline": a["delta"]["model_beats_baseline"],
        }
    board["gate_C_G2"] = rep["gate_C_G2"]
    board["n_records"] = int(len(dataset()))
    return board


# ---- external submission interface (challenge style) -----------------------------------------
@dataclass
class Submission:
    name: str
    predict_fn: Callable[[dict], Any] # public_input -> {"efficiency_pct": float}


def public_inputs():
    """Each dataset row as a public input (features shown; the measured efficiency label hidden)."""
    df = dataset()
    pub = []
    for _, r in df.iterrows():
        pub.append({"task_id": f"we_{r['system']}_{r['locus']}_{r['cell_type']}", "family": r["family"],
                    "write_type": r["write_type"], "variant": r["variant"], "cargo_bp": int(r["cargo_bp"]),
                    "locus": r["locus"], "cell_type": r["cell_type"], "delivery": r["delivery"],
                    "instructions": "return {'efficiency_pct': float in [0,100]}"})
    return pub


def evaluate(submission: Submission) -> dict:
    """Score an external submission (MAE + Spearman over the dataset; deterministic; non-circular)."""
    import numpy as np
    from scipy.stats import spearmanr
    df = dataset()
    pub = public_inputs()
    pred, ok = [], True
    for pi in pub:
        try:
            pred.append(float(submission.predict_fn(dict(pi))["efficiency_pct"]))
        except Exception: # noqa: BLE001 - abstain/err on a row -> worst-case, never crash the bench
            pred.append(0.0)
            ok = False
    y = df["efficiency_pct"].to_numpy()
    pred = np.array(pred)
    return {"submission": submission.name, "n": int(len(df)), "mae": float(np.mean(np.abs(y - pred))),
            "spearman": float(spearmanr(pred, y).statistic), "no_crash": ok}
