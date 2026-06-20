"""Learned cross-family writer-efficiency predictor behind Stage C (v6.8 PEN-WRITER, C-WS2).

Given `(family, variant-is-evolved, write-type, cargo size, locus context, cell-type class)`, predict the
integration **efficiency (%)** with a conformal interval, candidate-flagged. The baseline-to-beat is the
curated-KB prior (a writer's family-mean efficiency; the KB ranks by family). Gate C-G2 (pre-registered): the
learned model ships behind Stage C ONLY if it beats the family-mean baseline on **held-out family AND held-out
locus** (paired-bootstrap CI excludes 0); otherwise the KB ranking is retained and the negative is reported.
Never tune to the test.

This is a SMALL curated dataset (~38 human-cell records across 4 families), the benchmark + the dataset are the
standalone contribution, and a negative result is an expected outcome. Features are deliberately
interpretable (no ESM/Evo2 embeddings here, at N=38 they would overfit; variant *scoring* uses ESM3/Evo2 in
`design.writer_variants`). Every efficiency is a real published number (see `writer_efficiency`); nothing invented.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from pen_stack.atlas.writer_efficiency import human_cell
from pen_stack.wgenome.uncertainty import ConformalRegressor

# interpretable feature construction -------------------------------------------------------------
_PRIMARY = {"primary_T", "primary_hepatocyte", "primary_fibroblast", "hepatocyte_in_vivo", "iPSC"}
_AGG_LOCI = {"8loci_avg", "14loci_avg", "endogenous_avg", "best_locus", "human_genome", "multi_human"}


def _evolved(variant: str) -> int:
    v = str(variant).lower()
    wt = v in ("wt", "wt_bxb1") or v.startswith("wt")
    return 0 if wt else 1


def _celltype_class(ct: str) -> str:
    if ct in _PRIMARY:
        return "primary_or_ipsc"
    return "cell_line"


def featurize(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)
    f["family"] = df["family"].astype("category")
    f["evolved"] = df["variant"].map(_evolved).astype(int)
    f["log_cargo"] = np.log10(df["cargo_bp"].astype(float).clip(lower=1))
    f["cell_class"] = df["cell_type"].map(_celltype_class).astype("category")
    f["delivery"] = df["delivery"].astype("category")
    return f


def specific_locus_mask(df: pd.DataFrame) -> np.ndarray:
    """True for rows at a SPECIFIC named locus (excludes aggregate/avg/genome-wide pseudo-loci)."""
    return ~df["locus"].isin(_AGG_LOCI)


# baselines --------------------------------------------------------------------------------------
def _family_mean_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """The KB prior: predict a row's efficiency as the train family-mean (falls back to the global train mean
    for an unseen family, which is exactly what happens under held-out-family)."""
    gm = float(train["efficiency_pct"].mean())
    fam_mean = train.groupby("family")["efficiency_pct"].mean().to_dict()
    return np.array([fam_mean.get(f, gm) for f in test["family"]], float)


# model ------------------------------------------------------------------------------------------
def _fit_gbr(Xtr, ytr, seed: int = 42):
    """Small, regularized GBR, appropriate for ~38 points (shallow, few estimators). One-hot the categoricals."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(max_depth=2, max_iter=120, learning_rate=0.05,
                                      l2_regularization=1.0, min_samples_leaf=4, random_state=seed)
    m.fit(Xtr, ytr)
    return m


def _encode(f_train: pd.DataFrame, f_test: pd.DataFrame):
    """One-hot encode categoricals consistently across train/test."""
    cat = ["family", "cell_class", "delivery"]
    num = ["evolved", "log_cargo"]
    Xtr = pd.get_dummies(f_train[cat + num], columns=cat).astype(float)
    Xte = pd.get_dummies(f_test[cat + num], columns=cat).reindex(columns=Xtr.columns, fill_value=0.0).astype(float)
    return Xtr, Xte


@dataclass
class WriterEfficiencyModel:
    columns: list[str] = field(default_factory=list)
    model: object | None = None
    conformal: ConformalRegressor | None = None
    meta: dict = field(default_factory=dict)

    def fit(self, df: pd.DataFrame | None = None, seed: int = 42) -> "WriterEfficiencyModel":
        df = human_cell(strict=False) if df is None else df
        f = featurize(df)
        X = pd.get_dummies(f[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                           columns=["family", "cell_class", "delivery"]).astype(float)
        self.columns = list(X.columns)
        self.model = _fit_gbr(X, df["efficiency_pct"].to_numpy(), seed)
        self.meta = {"n": int(len(df)), "families": sorted(df["family"].unique()),
                     "efficiency_units": "percent_integration"}
        return self

    def _design_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        f = featurize(df)
        X = pd.get_dummies(f[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                           columns=["family", "cell_class", "delivery"]).astype(float)
        return X.reindex(columns=self.columns, fill_value=0.0)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self._design_matrix(df))

    def predict_interval(self, df: pd.DataFrame) -> dict:
        yhat = self.predict(df)
        if self.conformal is None or not np.isfinite(self.conformal.qhat):
            return {"yhat": yhat, "lo": None, "hi": None, "interval_kind": "uncalibrated"}
        lo, hi = self.conformal.interval(yhat)
        return {"yhat": yhat, "lo": np.clip(lo, 0, 100), "hi": np.clip(hi, 0, 100),
                "nominal_coverage": 1 - self.conformal.alpha,
                "interval_kind": "trained split-conformal (% integration; candidate)"}

    def save(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump({"columns": self.columns, "model": self.model, "conformal": self.conformal,
                         "meta": self.meta}, fh)
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "WriterEfficiencyModel":
        with open(path, "rb") as fh:
            return cls(**pickle.load(fh))


# evaluation: leave-one-family-out + leave-one-locus-out, learned vs KB family-mean baseline -----
def _loo_groups(df: pd.DataFrame, by: str):
    vals = df[by].to_numpy()
    for g in pd.unique(vals):
        te = np.where(vals == g)[0]
        tr = np.where(vals != g)[0]
        if len(tr) >= 6 and len(te) >= 1:
            yield g, tr, te


def _boot_delta(model_err, base_err, reps=2000, seed=20260620):
    """Paired bootstrap 95% CI on mean(base_err) - mean(model_err) (positive = model better, lower error)."""
    rng = np.random.default_rng(seed)
    me, be = np.asarray(model_err, float), np.asarray(base_err, float)
    n = len(me)
    d = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        d.append(float(np.mean(be[idx]) - np.mean(me[idx])))
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"delta_mean_abs_err_reduction": float(np.mean(d)), "ci95": [float(lo), float(hi)],
            "model_beats_baseline": bool(lo > 0)}


def evaluate(df: pd.DataFrame | None = None, seed: int = 42) -> dict:
    """Held-out-family AND held-out-locus CV: learned model vs the KB family-mean baseline. Reports Spearman,
    MAE, and the paired-bootstrap CI on the MAE reduction. Gate C-G2 = beats baseline on BOTH axes (CI excludes 0)."""
    df = human_cell(strict=False).reset_index(drop=True) if df is None else df.reset_index(drop=True)
    out = {"n": int(len(df)), "n_families": int(df["family"].nunique())}
    for axis, by, sub in (("held_out_family", "family", df),
                          ("held_out_locus", "locus", df[specific_locus_mask(df)].reset_index(drop=True))):
        y_true, y_model, y_base = [], [], []
        for _g, tr, te in _loo_groups(sub, by):
            tr_df, te_df = sub.iloc[tr], sub.iloc[te]
            f = featurize(tr_df)
            Xtr = pd.get_dummies(f[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                                 columns=["family", "cell_class", "delivery"]).astype(float)
            m = _fit_gbr(Xtr, tr_df["efficiency_pct"].to_numpy(), seed)
            fte = featurize(te_df)
            Xte = pd.get_dummies(fte[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                                 columns=["family", "cell_class", "delivery"]).reindex(columns=Xtr.columns,
                                                                                       fill_value=0.0).astype(float)
            y_true.extend(te_df["efficiency_pct"].tolist())
            y_model.extend(m.predict(Xte).tolist())
            y_base.extend(_family_mean_baseline(tr_df, te_df).tolist())
        y_true, y_model, y_base = map(np.array, (y_true, y_model, y_base))
        if len(y_true) < 3:
            out[axis] = {"available": False, "n": int(len(y_true))}
            continue
        me = np.abs(y_true - y_model)
        be = np.abs(y_true - y_base)
        out[axis] = {
            "n": int(len(y_true)),
            "mae_model": float(np.mean(me)), "mae_baseline_family_mean": float(np.mean(be)),
            "spearman_model": float(spearmanr(y_model, y_true).statistic),
            "spearman_baseline": float(spearmanr(y_base, y_true).statistic),
            "delta": _boot_delta(me, be, seed=seed),
        }
    mf = out.get("held_out_family", {}).get("delta", {}).get("model_beats_baseline", False)
    ml = out.get("held_out_locus", {}).get("delta", {}).get("model_beats_baseline", False)
    out["gate_C_G2"] = {
        "beats_on_held_out_family": bool(mf), "beats_on_held_out_locus": bool(ml),
        "ship_learned_model": bool(mf and ml),
        "verdict": ("learned predictor beats the KB family-mean baseline on BOTH held-out family AND locus, "
                    "serve it (candidate-flagged)" if (mf and ml) else
                    "learned predictor does NOT beat the KB baseline on both axes at this N, RETAIN the KB "
                    "ranking, report the negative; the curated dataset + Writer-Efficiency Bench are the "
                    "contribution (the pre-registered outcome)")}
    return out


def calibrate(df: pd.DataFrame | None = None, alpha: float = 0.10, seed: int = 42) -> ConformalRegressor:
    """Leave-one-family-out OOF residuals → split-conformal interval on the % scale (family-blocked)."""
    df = human_cell(strict=False).reset_index(drop=True) if df is None else df.reset_index(drop=True)
    y_true, y_hat = [], []
    for _g, tr, te in _loo_groups(df, "family"):
        tr_df, te_df = df.iloc[tr], df.iloc[te]
        f = featurize(tr_df)
        Xtr = pd.get_dummies(f[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                             columns=["family", "cell_class", "delivery"]).astype(float)
        m = _fit_gbr(Xtr, tr_df["efficiency_pct"].to_numpy(), seed)
        fte = featurize(te_df)
        Xte = pd.get_dummies(fte[["family", "cell_class", "delivery", "evolved", "log_cargo"]],
                             columns=["family", "cell_class", "delivery"]).reindex(columns=Xtr.columns,
                                                                                   fill_value=0.0).astype(float)
        y_true.extend(te_df["efficiency_pct"].tolist())
        y_hat.extend(m.predict(Xte).tolist())
    return ConformalRegressor(alpha=alpha).calibrate(np.array(y_true), np.array(y_hat))
