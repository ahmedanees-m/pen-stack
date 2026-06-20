"""Falsification controls for the v6.7 position-effect model (WS-V).

If the learned signal is real, destroying the label must destroy the prediction. `label_shuffle_control` permutes
the expression labels and re-runs the chromosome-blocked CV: the model's Spearman must collapse to ~chance. A
model that still "predicts" shuffled labels is leaking, not learning.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr
from sklearn.model_selection import GroupKFold

from pen_stack.twin.position_effect import _feats, _lgb_reg


def _quick_cv_rho(df, seed: int = 42) -> float:
    """Light chromosome-blocked OOF Spearman (no bootstrap), for the controls."""
    feats = _feats(df)
    X = df[feats].astype("float32").fillna(0.0)
    y = df["expression_raw"].to_numpy()
    g = df["chrom"].astype("category").cat.codes.to_numpy()
    k = min(5, len(np.unique(g)))
    oof = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=k).split(X, y, g):
        oof[te] = _lgb_reg(seed).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    return float(spearmanr(oof, y).statistic)


def label_shuffle_control(df, seed: int = 0, chance_tol: float = 0.10) -> dict:
    """Permute expression labels -> chromosome-blocked CV Spearman must collapse to ~0 (chance). Returns the
    real rho, the shuffled rho, and whether the control passes (shuffled ~ chance AND well below real)."""
    real = _quick_cv_rho(df, seed=42)
    d = df.copy()
    rng = np.random.default_rng(seed)
    d["expression_raw"] = rng.permutation(d["expression_raw"].to_numpy())
    shuffled = _quick_cv_rho(d, seed=42)
    return {"rho_real": round(real, 4), "rho_shuffled": round(shuffled, 4),
            "is_chance": bool(abs(shuffled) < chance_tol),
            "passes": bool(abs(shuffled) < chance_tol and real - abs(shuffled) > 0.1)}
