"""Durability layer (Phase 1, Step 1.7) — the conditional chromatin-context model.

Learns ONE function: `local chromatin features -> (expression level, silenced/stable)` on TRIP
integrations. The model never sees a coordinate, so it is cell-type-agnostic in function: to score a
new cell type you supply its chromatin tracks. This is the layer no safe-harbour resource provides,
and TRIP supervises exactly the writing-relevant quantity (position effect on an integrated cassette).
"""
from __future__ import annotations

import os
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyBigWig
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

# canonical chromatin feature names (must match across mouse training + human application)
CHROMATIN = ["atac", "dnase", "H3K27ac", "H3K4me1", "H3K4me3", "H3K9me3", "H3K27me3"]


def liftover_positions(df: pd.DataFrame, chain_file: str) -> pd.DataFrame:
    """Lift (chrom,pos) with a UCSC chain (e.g. mm9->mm10). Drops positions that fail to lift."""
    from pyliftover import LiftOver
    lo = LiftOver(chain_file)
    out = []
    for _, r in df.iterrows():
        c = lo.convert_coordinate(r["chrom"], int(r["pos"]))
        if c:
            row = r.to_dict()
            row["chrom"], row["pos"] = c[0][0], c[0][1]
            out.append(row)
    return pd.DataFrame(out)


def extract_chromatin_at(df: pd.DataFrame, panel: dict, raw_dir: str, download_fn,
                         window: int = 2500) -> pd.DataFrame:
    """Point-query each bigWig's mean signal in +/-window around each integration position.
    Only the integration sites are queried (no genome-wide binning needed)."""
    out = df.copy()
    for name, rec in panel.items():
        path = download_fn(rec["href"], os.path.join(raw_dir, f"mES_{name}_{rec['accession']}.bigWig"))
        bw = pyBigWig.open(path)
        chroms = set(bw.chroms().keys())
        vals = []
        for chrom, pos in zip(out["chrom"], out["pos"]):
            key = chrom if chrom in chroms else chrom.replace("chr", "")
            if key not in chroms:
                vals.append(0.0)
                continue
            try:
                v = bw.stats(key, max(0, pos - window), pos + window, type="mean")[0]
            except (RuntimeError, IndexError):
                v = None
            vals.append(0.0 if v is None else float(v))
        out[name] = vals
        bw.close()
        os.remove(path)
        print(f"  extracted {name} at {len(out)} sites", flush=True)
    return out


def train_durability(trip_df: pd.DataFrame, seed: int = 42) -> dict:
    feats = [c for c in CHROMATIN if c in trip_df.columns]
    df = trip_df.dropna(subset=feats + ["expression"]).copy()
    X = df[feats].astype("float32").fillna(0.0)
    y_expr = df["expression"].to_numpy()
    y_sil = df["silenced"].astype(int).to_numpy()
    groups = df["chrom"].astype("category").cat.codes.to_numpy()

    gkf = GroupKFold(n_splits=min(5, len(np.unique(groups))))
    oof_expr = np.zeros(len(df))
    oof_sil = np.zeros(len(df))
    for tr, te in gkf.split(X, y_expr, groups):
        reg = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=31,
                                subsample=0.8, random_state=seed, n_jobs=-1, verbosity=-1).fit(X.iloc[tr], y_expr[tr])
        oof_expr[te] = reg.predict(X.iloc[te])
        clf = lgb.LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31,
                                 subsample=0.8, random_state=seed, n_jobs=-1, verbosity=-1).fit(X.iloc[tr], y_sil[tr])
        oof_sil[te] = clf.predict_proba(X.iloc[te])[:, 1]

    rho = float(spearmanr(oof_expr, y_expr).statistic)
    auroc = float(roc_auc_score(y_sil, oof_sil))
    # baseline: H3K9me3 (heterochromatin) alone as a silencing predictor, and LAD-like (low ATAC) for expression
    base_sil = roc_auc_score(y_sil, df["H3K9me3"].fillna(0)) if "H3K9me3" in df else float("nan")
    base_expr = spearmanr(df.get("atac", pd.Series(0, index=df.index)).fillna(0), y_expr).statistic

    final_reg = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=31,
                                  random_state=seed, n_jobs=-1, verbosity=-1).fit(X, y_expr)
    imp = dict(sorted(zip(feats, final_reg.feature_importances_.tolist()), key=lambda kv: kv[1], reverse=True))
    return {
        "n": int(len(df)), "features": feats,
        "expr_spearman": rho, "expr_baseline_atac_spearman": float(base_expr),
        "silenced_auroc": auroc, "silenced_baseline_h3k9me3_auroc": float(base_sil),
        "feature_importance": imp, "reg": final_reg,
        "clf": lgb.LGBMClassifier(n_estimators=500, learning_rate=0.03, num_leaves=31,
                                  random_state=seed, n_jobs=-1, verbosity=-1).fit(X, y_sil),
    }


def save_models(res: dict, out_dir: str, tag: str = "durability") -> None:
    import pickle
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{out_dir}/{tag}.pkl", "wb") as fh:
        pickle.dump({"reg": res["reg"], "clf": res["clf"], "features": res["features"]}, fh)
