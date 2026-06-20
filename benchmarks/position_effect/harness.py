"""TPE-Bench, the position-effect / expression track for the Genome-Writing Challenge (v6.7 PEN-EXPRESS, WS-B).

The expression capability never had a held-out benchmark. TPE-Bench seals a held-out split of the TRIP
position-effect supervision and scores a `predict_fn(public_input) -> {expression, p_silenced}` on it, with a
baseline leaderboard (cassette-only, context-only durability head, PEN-EXPRESS factored model). Two tracks:

  * `chrom_holdout` (LIVE): held-out CHROMOSOMES (frozen in split.json, SHA-locked), leakage-controlled, sealed
    before model selection. Metric = Spearman rho (expression) + AUROC (silenced).
  * `celltype_holdout` (DATA-GATED): leave-one-cell-type-out, the headline transfer track. With a single
    available cell type (mESC) it reports `data_gated`; it activates once PatchMPRA/MPIRE/lentiMPRA/
    Leemans are fetched. No fabricated transfer number.

No circular labels (the label is the measured TRIP expression, not a submitter claim); deterministic; the
PEN-EXPRESS model anchors the leaderboard. The public input shows chromatin context + cassette, never the label.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from pen_stack.twin.data.position_effect import FEATURE_COLS, load_position_effect

_HERE = Path(__file__).resolve().parent


def _split_spec() -> dict:
    return json.loads((_HERE / "split.json").read_text(encoding="utf-8"))


def load_split():
    """Return (train_df, test_df) by the SEALED held-out-chromosome split (split.json). Deterministic."""
    spec = _split_spec()
    df = load_position_effect(datasets=spec.get("datasets") or None)
    test_chroms = set(spec["chrom_holdout"]["test_chroms"])
    te = df[df["chrom"].isin(test_chroms)].reset_index(drop=True)
    tr = df[~df["chrom"].isin(test_chroms)].reset_index(drop=True)
    return tr, te


def _feats(df):
    return [c for c in FEATURE_COLS if c in df.columns]


def score_predictions(pred_expr, test_df, pred_sil=None) -> dict:
    """Spearman rho on expression (+ AUROC on silenced if provided) over the sealed test rows."""
    y = test_df["expression_raw"].to_numpy()
    out = {"n": int(len(test_df)), "expression_spearman": float(spearmanr(pred_expr, y).statistic)}
    if pred_sil is not None:
        ys = test_df["silenced"].astype(int).to_numpy()
        out["silenced_auroc"] = float(roc_auc_score(ys, pred_sil)) if len(np.unique(ys)) > 1 else None
    return out


# ---- baselines (the leaderboard anchors) -----------------------------------------------------
def _train_baselines(tr):
    from pen_stack.twin.position_effect import PositionEffectModel, _lgb_clf, _lgb_reg
    feats = _feats(tr)
    Xtr = tr[feats].astype("float32").fillna(0.0)
    # cassette-only
    cm = {str(c): float(g["expression_raw"].mean()) for c, g in tr.groupby("cassette")}
    gm = float(tr["expression_raw"].mean())
    # context-only durability head
    ctx_reg = _lgb_reg().fit(Xtr, tr["expression_raw"].to_numpy())
    ctx_clf = _lgb_clf().fit(Xtr, tr["silenced"].astype(int).to_numpy())
    # PEN-EXPRESS factored model
    pe = PositionEffectModel().fit(tr)
    return {"cassette_means": cm, "global_mean": gm, "ctx_reg": ctx_reg, "ctx_clf": ctx_clf,
            "pe": pe, "feats": feats}


def baseline_leaderboard() -> dict:
    """Train each baseline on the sealed TRAIN chromosomes, score on the sealed TEST chromosomes. Real numbers."""
    tr, te = load_split()
    b = _train_baselines(tr)
    feats = b["feats"]
    Xte = te[feats].astype("float32").fillna(0.0)
    rows = {}
    # cassette-only
    cas = np.array([b["cassette_means"].get(str(c), b["global_mean"]) for c in te["cassette"]])
    rows["cassette_only"] = score_predictions(cas, te)
    # context-only durability head
    rows["context_only_durability_head"] = score_predictions(
        b["ctx_reg"].predict(Xte), te, b["ctx_clf"].predict_proba(Xte)[:, 1])
    # PEN-EXPRESS factored
    rows["pen_express_factored"] = score_predictions(
        b["pe"].predict_expression(te), te, b["pe"].predict_silenced(te))
    spec = _split_spec()
    return {"track": "chrom_holdout", "sealed_test_chroms": spec["chrom_holdout"]["test_chroms"],
            "n_train": int(len(tr)), "n_test": int(len(te)), "leaderboard": rows,
            "celltype_holdout": celltype_track()}


def celltype_track() -> dict:
    """The headline leave-one-cell-type-out transfer track, data-gated until >=2 cell types exist."""
    from pen_stack.twin.data.position_effect import heldout_celltype_splits
    df = load_position_effect()
    splits = heldout_celltype_splits(df)
    if not splits:
        return {"status": "data_gated", "available_cell_types": sorted(df["cell_type"].unique()),
                "note": "leave-one-cell-type-out needs >=2 cell types; activates on PatchMPRA/MPIRE/lentiMPRA/"
                        "Leemans acquisition. No transfer number is fabricated."}
    return {"status": "live", "n_folds": len(splits)}


# ---- external submission interface (challenge style) -----------------------------------------
@dataclass
class Submission:
    name: str
    predict_fn: Callable[[dict], Any] # public_input -> {"expression": float, "p_silenced": float?}


def public_inputs():
    """The sealed test rows as public inputs (chromatin context + cassette shown; label hidden)."""
    _, te = load_split()
    feats = _feats(te)
    pub = []
    for _, r in te.iterrows():
        pub.append({"task_id": f"pe_{r['dataset']}_{r['chrom']}_{int(r['pos'])}", "family": "position_effect",
                    "cassette": r["cassette"], "chromatin_features": {f: float(r[f]) for f in feats},
                    "instructions": "return {'expression': float, 'p_silenced': float in [0,1]}"})
    return pub


def evaluate(submission: Submission) -> dict:
    """Score an external submission on the sealed test (deterministic; non-circular; no-fabrication checked)."""
    _, te = load_split()
    pub = public_inputs()
    pe, psil, ok = [], [], True
    for pi in pub:
        try:
            ans = submission.predict_fn(dict(pi))
            pe.append(float(ans.get("expression")))
            psil.append(float(ans["p_silenced"]) if ans.get("p_silenced") is not None else np.nan)
        except Exception: # noqa: BLE001 - a submission may abstain/err on a row; it just loses signal there
            pe.append(0.0)
            psil.append(np.nan)
            ok = False
    sil = np.array(psil)
    res = score_predictions(np.array(pe), te, sil if np.isfinite(sil).all() else None)
    res.update({"submission": submission.name, "track": "chrom_holdout", "no_crash": ok})
    return res
