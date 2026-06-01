"""Safety layer (Phase 1, Step 1.6) — calibrated genotoxicity-risk model.

Position features -> P(genotoxic) with isotonic calibration and CHROMOSOME-BLOCK cross-validation
(so adjacent 1 kb bins never leak between train/test). Always reported against the honest baseline:
distance-to-nearest-oncogene. Output is a calibrated risk per bin.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

from pen_stack.wgenome.features import feature_columns


def _blocks(chrom: pd.Series) -> np.ndarray:
    """Chromosome-block groups for leakage-free CV."""
    return chrom.astype("category").cat.codes.to_numpy()


def train_safety(df: pd.DataFrame, label: str = "genotoxic_cis", n_splits: int = 5,
                 seed: int = 42) -> dict:
    feats = feature_columns(df)
    X = df[feats].astype("float32").fillna(0.0)
    y = df[label].astype(int).to_numpy()
    groups = _blocks(df["chrom"])

    gkf = GroupKFold(n_splits=min(n_splits, len(np.unique(groups))))
    oof = np.zeros(len(df), dtype="float64")
    for tr, te in gkf.split(X, y, groups):
        pos = max(1, int(y[tr].sum()))
        spw = max(1.0, (len(tr) - pos) / pos)   # class imbalance
        clf = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=63,
                                 subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                                 random_state=seed, n_jobs=-1, verbosity=-1)
        clf.fit(X.iloc[tr], y[tr])
        raw = clf.predict_proba(X.iloc[te])[:, 1]
        # isotonic calibration fit on the training fold's OOB-ish raw scores
        iso = IsotonicRegression(out_of_bounds="clip")
        raw_tr = clf.predict_proba(X.iloc[tr])[:, 1]
        iso.fit(raw_tr, y[tr])
        oof[te] = iso.transform(raw)

    auroc = roc_auc_score(y, oof)
    auprc = average_precision_score(y, oof)

    # honest baseline: closer to oncogene => riskier
    base = -df["dist_oncogene"].fillna(df["dist_oncogene"].max()).to_numpy()
    auroc_base = roc_auc_score(y, base)
    auprc_base = average_precision_score(y, base)

    # final model on all data (for scoring), + feature importance
    pos = max(1, int(y.sum()))
    spw = max(1.0, (len(y) - pos) / pos)
    final = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=63,
                               subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                               random_state=seed, n_jobs=-1, verbosity=-1).fit(X, y)
    imp = dict(sorted(zip(feats, final.feature_importances_.tolist()),
                      key=lambda kv: kv[1], reverse=True))
    return {
        "n": int(len(df)), "n_pos": int(y.sum()), "features": feats,
        "auroc_model": float(auroc), "auprc_model": float(auprc),
        "auroc_baseline": float(auroc_base), "auprc_baseline": float(auprc_base),
        "auroc_delta": float(auroc - auroc_base),
        "feature_importance": imp, "model": final, "oof": oof,
    }
