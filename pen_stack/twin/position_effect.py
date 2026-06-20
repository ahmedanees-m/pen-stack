"""Learned cassette x context position-effect model behind Stage H (v6.7 PEN-EXPRESS, WS-M + WS-U).

Replaces the closed-form expression heuristic with a learned, **trained-conformal** model. Factored, decomposable
(not opaque):

    E_raw ~= f_cassette(cassette) # the cassette's intrinsic strength (per-cassette mean)
            + g_context(chromatin features) # the position effect, a LightGBM on local chromatin
            (+ h_interaction, reported) # does the context function differ by cassette? (separability)

`g_context` is supervised on the residual `E_raw - f_cassette`, so it learns the *position* effect on a scale
comparable across cassettes. A `silenced` classifier shares the same features. Both are wrapped with the EXISTING
`wgenome.uncertainty.ConformalRegressor` (chromosome-Mondrian) and `wgenome.ood.OODDetector`, so a prediction is a
*calibrated interval that widens out of distribution*, which is exactly the "trained conformal" property Stage H
lacked (it was a heuristic +/-0.20 band).

Gate (pre-registered, G-M): the learned model ships behind Stage H ONLY if it beats the v3.x durability head
(context-only) AND the heuristic on chromosome-blocked CV; otherwise the baseline is retained and the negative is
reported. Never tune to the test. No fabrication: every metric here comes from a real CV run on real supervision.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from pen_stack.twin.data.position_effect import FEATURE_COLS
from pen_stack.wgenome.ood import OODDetector
from pen_stack.wgenome.uncertainty import ConformalRegressor

_LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, subsample=0.8,
            random_state=42, n_jobs=-1, verbosity=-1)


def _lgb_reg(seed: int = 42):
    import lightgbm as lgb
    return lgb.LGBMRegressor(**{**_LGB, "random_state": seed})


def _lgb_clf(seed: int = 42):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**{**_LGB, "random_state": seed})


def _feats(df: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLS if c in df.columns]


def _groups(df: pd.DataFrame) -> np.ndarray:
    return df["chrom"].astype("category").cat.codes.to_numpy()


def _boot_delta_ci(a_pred, b_pred, y, kind: str, groups=None, reps: int = 2000, seed: int = 20260619):
    """Paired bootstrap 95% CI on (metric(a) - metric(b)). kind in {'spearman','auroc'}. Resamples whole
    chromosome groups when `groups` is given (respects the blocked structure), else rows."""
    rng = np.random.default_rng(seed)
    a_pred, b_pred, y = map(lambda x: np.asarray(x, float), (a_pred, b_pred, y))
    n = len(y)

    def _metric(p, yy):
        if kind == "spearman":
            return spearmanr(p, yy).statistic
        return roc_auc_score(yy.astype(int), p) if len(np.unique(yy)) > 1 else np.nan

    if groups is not None:
        groups = np.asarray(groups)
        uniq = np.unique(groups)
        members = {g: np.where(groups == g)[0] for g in uniq}
    deltas = []
    for _ in range(reps):
        if groups is not None:
            pick = rng.choice(uniq, size=len(uniq), replace=True)
            idx = np.concatenate([members[g] for g in pick])
        else:
            idx = rng.integers(0, n, n)
        if len(np.unique(y[idx])) < 2 and kind == "auroc":
            continue
        deltas.append(_metric(a_pred[idx], y[idx]) - _metric(b_pred[idx], y[idx]))
    deltas = np.asarray([d for d in deltas if np.isfinite(d)])
    if not len(deltas):
        return {"delta_mean": float("nan"), "ci95": [float("nan"), float("nan")], "excludes_zero": False}
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {"delta_mean": float(np.mean(deltas)), "ci95": [float(lo), float(hi)],
            "excludes_zero": bool(lo > 0 or hi < 0)}


@dataclass
class PositionEffectModel:
    """The learned, factored, trained-conformal position-effect model. Decomposable: `cassette_means`
    (f_cassette), `reg` (g_context on the residual), `clf` (silenced), `conformal` (interval), `ood` (widening)."""
    features: list[str] = field(default_factory=list)
    cassette_means: dict = field(default_factory=dict)
    global_mean: float = 0.0
    reg: object | None = None # g_context: chromatin -> residual expression
    clf: object | None = None # silenced classifier
    conformal: ConformalRegressor | None = None
    ood: OODDetector | None = None
    meta: dict = field(default_factory=dict)

    # ---- fit ------------------------------------------------------------------------------------
    def fit(self, df: pd.DataFrame, seed: int = 42) -> "PositionEffectModel":
        self.features = _feats(df)
        self.global_mean = float(df["expression_raw"].mean())
        self.cassette_means = {str(c): float(g["expression_raw"].mean())
                               for c, g in df.groupby("cassette")}
        resid = df["expression_raw"].to_numpy() - self._f_cassette(df["cassette"])
        X = df[self.features].astype("float32").fillna(0.0)
        self.reg = _lgb_reg(seed).fit(X, resid)
        self.clf = _lgb_clf(seed).fit(X, df["silenced"].astype(int).to_numpy())
        self.ood = OODDetector(method="mahalanobis").fit(X.to_numpy())
        self.meta = {"n": int(len(df)), "features": self.features,
                     "cassettes": list(self.cassette_means), "global_mean": self.global_mean,
                     "expr_min": float(df["expression_raw"].min()),
                     "expr_max": float(df["expression_raw"].max()),
                     "datasets": sorted(df["dataset"].unique()), "cell_types": sorted(df["cell_type"].unique())}
        return self

    def relative(self, yhat: float) -> float | None:
        """Monotone min-max rescale of the native (log2) prediction to [0,1] over the training range, for
        UI comparability with the mechanistic relative_expression. Clearly a rescale, not a new quantity."""
        lo, hi = self.meta.get("expr_min"), self.meta.get("expr_max")
        if lo is None or hi is None or hi <= lo:
            return None
        return float(min(1.0, max(0.0, (float(yhat) - lo) / (hi - lo))))

    def _f_cassette(self, cassette: pd.Series | list) -> np.ndarray:
        return np.array([self.cassette_means.get(str(c), self.global_mean) for c in cassette], float)

    # ---- point prediction (decomposed) ----------------------------------------------------------
    def predict_expression(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.features].astype("float32").fillna(0.0)
        return self._f_cassette(df["cassette"]) + self.reg.predict(X)

    def predict_silenced(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.features].astype("float32").fillna(0.0)
        return self.clf.predict_proba(X)[:, 1]

    # ---- interval (trained conformal, OOD-widened) ----------------------------------------------
    def predict_interval(self, df: pd.DataFrame) -> dict:
        yhat = self.predict_expression(df)
        if self.conformal is None or not np.isfinite(self.conformal.qhat):
            return {"yhat": yhat, "lo": None, "hi": None, "interval_kind": "uncalibrated (no conformal qhat)"}
        X = df[self.features].astype("float32").fillna(0.0).to_numpy()
        widen = self.ood.widen_factor(X) if self.ood is not None else np.ones(len(df))
        lo, hi = self.conformal.interval(yhat, sigma=widen)
        return {"yhat": yhat, "lo": lo, "hi": hi, "ood_widen": widen,
                "nominal_coverage": 1 - self.conformal.alpha,
                "interval_kind": "trained split-conformal (chromosome-blocked OOF; per-chromosome Mondrian qhats "
                                 "computed, GLOBAL qhat served, a query has no chromosome at serve time), OOD-widened"}

    # ---- persistence ----------------------------------------------------------------------------
    def save(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump({"features": self.features, "cassette_means": self.cassette_means,
                         "global_mean": self.global_mean, "reg": self.reg, "clf": self.clf,
                         "conformal": self.conformal, "ood": self.ood, "meta": self.meta}, fh)
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "PositionEffectModel":
        with open(path, "rb") as fh:
            d = pickle.load(fh)
        return cls(**d)


# --------------------------------------------------------------------------------------------------
# evaluation: chromosome-blocked CV, learned model vs context-only durability-head baseline
# --------------------------------------------------------------------------------------------------
def evaluate(df: pd.DataFrame, seed: int = 42, n_splits: int = 5) -> dict:
    """Chromosome-blocked GroupKFold OOF. Compares the FACTORED model (f_cassette + g_context) to the
    CONTEXT-ONLY baseline (the v3.x durability head: chromatin -> expression, no cassette term) and to a
    cassette-only baseline. Reports expression Spearman, silenced AUROC, paired bootstrap CIs on the deltas,
    and the interaction (separability) variance share. Returns OOF arrays for conformal calibration (WS-U).
    """
    feats = _feats(df)
    X = df[feats].astype("float32").fillna(0.0)
    y = df["expression_raw"].to_numpy()
    ysil = df["silenced"].astype(int).to_numpy()
    cassette = df["cassette"]
    g = _groups(df)
    k = min(n_splits, len(np.unique(g)))
    gkf = GroupKFold(n_splits=k)

    oof_factored = np.zeros(len(df))
    oof_context = np.zeros(len(df)) # durability head = chromatin-only
    oof_cassette = np.zeros(len(df)) # cassette-only (f_cassette)
    oof_sil_factored = np.zeros(len(df))
    oof_sil_context = np.zeros(len(df))
    oof_resid = np.full(len(df), np.nan)

    for tr, te in gkf.split(X, y, g):
        cm = {str(c): float(y[tr][cassette.iloc[tr] == c].mean()) for c in cassette.iloc[tr].unique()}
        gm = float(y[tr].mean())
        f_tr = np.array([cm.get(str(c), gm) for c in cassette.iloc[tr]])
        f_te = np.array([cm.get(str(c), gm) for c in cassette.iloc[te]])
        # factored: cassette mean + g_context on residual
        reg_ctx = _lgb_reg(seed).fit(X.iloc[tr], y[tr] - f_tr)
        oof_factored[te] = f_te + reg_ctx.predict(X.iloc[te])
        oof_resid[te] = y[te] - oof_factored[te]
        # context-only baseline (durability head): chromatin -> expression directly
        reg_base = _lgb_reg(seed).fit(X.iloc[tr], y[tr])
        oof_context[te] = reg_base.predict(X.iloc[te])
        oof_cassette[te] = f_te
        # silenced: factored (cassette one-hot + chromatin) vs context-only
        cas_oh_tr = pd.get_dummies(cassette.iloc[tr]).astype("float32")
        cas_oh_te = pd.get_dummies(cassette.iloc[te]).reindex(columns=cas_oh_tr.columns, fill_value=0).astype("float32")
        Xf_tr = pd.concat([X.iloc[tr].reset_index(drop=True), cas_oh_tr.reset_index(drop=True)], axis=1)
        Xf_te = pd.concat([X.iloc[te].reset_index(drop=True), cas_oh_te.reset_index(drop=True)], axis=1)
        oof_sil_factored[te] = _lgb_clf(seed).fit(Xf_tr, ysil[tr]).predict_proba(Xf_te)[:, 1]
        oof_sil_context[te] = _lgb_clf(seed).fit(X.iloc[tr], ysil[tr]).predict_proba(X.iloc[te])[:, 1]

    rho_factored = float(spearmanr(oof_factored, y).statistic)
    rho_context = float(spearmanr(oof_context, y).statistic)
    rho_cassette = float(spearmanr(oof_cassette, y).statistic)
    auroc_factored = float(roc_auc_score(ysil, oof_sil_factored))
    auroc_context = float(roc_auc_score(ysil, oof_sil_context))

    # separability: variance share of the interaction term, fit g per cassette vs pooled on OOF residual scale
    inter = _interaction_share(df, feats, g, seed)

    return {
        "n": int(len(df)), "n_chrom_folds": int(k), "features": feats,
        "expression": {
            "rho_factored": rho_factored, "rho_context_only_durability_head": rho_context,
            "rho_cassette_only": rho_cassette,
            "delta_factored_vs_context": _boot_delta_ci(oof_factored, oof_context, y, "spearman", groups=g),
            "delta_factored_vs_cassette": _boot_delta_ci(oof_factored, oof_cassette, y, "spearman", groups=g),
        },
        "silenced": {
            "auroc_factored": auroc_factored, "auroc_context_only_durability_head": auroc_context,
            "delta_factored_vs_context": _boot_delta_ci(oof_sil_factored, oof_sil_context, ysil, "auroc", groups=g),
        },
        "separability": inter,
        "_oof": {"expression_pred": oof_factored, "expression_true": y, "residual": oof_resid,
                 "silenced_pred": oof_sil_factored, "silenced_true": ysil, "groups": g},
    }


def _interaction_share(df: pd.DataFrame, feats: list[str], g: np.ndarray, seed: int) -> dict:
    """How much does the context function differ BY cassette (the h_interaction term)? Compare a pooled
    g_context to per-cassette g_context on chromosome-blocked OOF; report the extra variance the interaction
    explains. With 1 cassette dominating, expect ~0 (additive suffices), reported either way."""
    X = df[feats].astype("float32").fillna(0.0)
    y = df["expression_raw"].to_numpy()
    cassette = df["cassette"]
    cms = {str(c): float(v["expression_raw"].mean()) for c, v in df.groupby("cassette")}
    resid = y - np.array([cms.get(str(c), y.mean()) for c in cassette])
    gkf = GroupKFold(n_splits=min(5, len(np.unique(g))))
    oof_pool = np.zeros(len(df))
    oof_inter = np.zeros(len(df))
    for tr, te in gkf.split(X, resid, g):
        oof_pool[te] = _lgb_reg(seed).fit(X.iloc[tr], resid[tr]).predict(X.iloc[te])
        # per-cassette model (interaction); fall back to pooled where a cassette is absent in train
        pred = oof_pool[te].copy()
        for c in cassette.iloc[te].unique():
            m_tr = (cassette.iloc[tr] == c).to_numpy()
            m_te = (cassette.iloc[te] == c).to_numpy()
            if m_tr.sum() >= 50:
                pred[m_te] = _lgb_reg(seed).fit(X.iloc[tr][m_tr], resid[tr][m_tr]).predict(X.iloc[te][m_te])
        oof_inter[te] = pred
    ss_tot = float(np.var(resid) * len(resid))
    r2_pool = 1 - float(np.sum((resid - oof_pool) ** 2)) / ss_tot if ss_tot else 0.0
    r2_inter = 1 - float(np.sum((resid - oof_inter) ** 2)) / ss_tot if ss_tot else 0.0
    return {"r2_pooled_context": round(r2_pool, 4), "r2_with_interaction": round(r2_inter, 4),
            "interaction_extra_r2": round(r2_inter - r2_pool, 4),
            "interpretation": ("interaction adds signal (cassette x context separability is real)"
                               if (r2_inter - r2_pool) > 0.01 else
                               "additive f_cassette + g_context suffices (no material interaction at this N)")}


def calibrate_conformal(oof: dict, alpha: float = 0.10) -> ConformalRegressor:
    """Trained split-conformal on the chromosome-blocked OOF residuals (Mondrian per chromosome group), the
    finite-sample (1-alpha) interval the EXISTING ConformalRegressor provides. This is what makes Stage H
    'trained conformal'. The shipped qhat is calibrated on ALL OOF residuals; true *held-out* coverage is
    reported separately by `conformal_heldout_coverage` (calibrating and evaluating on the same set would
    trivially hit nominal)."""
    y, yhat, groups = oof["expression_true"], oof["expression_pred"], oof["groups"]
    return ConformalRegressor(alpha=alpha).calibrate(y, yhat, groups=groups)


# --------------------------------------------------------------------------------------------------
# Stage-H serving seam, used by twin.outcome when a chromatin context is supplied (WS-I)
# --------------------------------------------------------------------------------------------------
_MODEL_CACHE: dict = {}


def load_cached_model(root=None) -> "PositionEffectModel | None":
    """Load the trained position-effect model if its artifact is present (VM/checkout); else None (installed
    library / CI -> Stage H falls back to the heuristic). Cached per root."""
    from pen_stack._resources import project_root
    root = root or project_root()
    key = str(root)
    if key not in _MODEL_CACHE:
        p = root / "models/position_effect.pkl"
        try:
            _MODEL_CACHE[key] = PositionEffectModel.load(p) if p.exists() else None
        except Exception: # noqa: BLE001 - corrupt/absent artifact -> heuristic fallback, never crash Stage H
            _MODEL_CACHE[key] = None
    return _MODEL_CACHE[key]


def predict_stage_h(design: dict, root=None) -> dict | None:
    """The learned, trained-conformal Stage-H position-effect prediction, returned ONLY when a chromatin
    context (the model's marks) is supplied AND the model artifact is present; else None and the caller
    falls back to the closed-form heuristic. No fabrication: missing context -> no learned claim."""
    model = load_cached_model(root)
    if model is None or not model.features:
        return None
    cf = design.get("chromatin_features")
    if not isinstance(cf, dict) and isinstance(design.get("chromatin_ctx"), dict):
        cf = design["chromatin_ctx"].get("features")
    if not isinstance(cf, dict):
        return None
    present = [f for f in model.features if f in cf]
    if len(present) < max(3, len(model.features) // 2): # need enough real context to be meaningful
        return None
    row = {f: float(cf.get(f, 0.0)) for f in model.features}
    cassette = str(design.get("cassette") or design.get("promoter")
                   or (next(iter(model.cassette_means), "_")))
    one = pd.DataFrame([{**row, "cassette": cassette}])
    iv = model.predict_interval(one)
    yhat = float(iv["yhat"][0])
    lo = float(iv["lo"][0]) if iv.get("lo") is not None else None
    hi = float(iv["hi"][0]) if iv.get("hi") is not None else None
    return {
        "predicted_log2_expression": round(yhat, 4),
        "interval_log2": [round(lo, 4), round(hi, 4)] if lo is not None else None,
        "relative_expression_learned": (round(model.relative(yhat), 4) if model.relative(yhat) is not None else None),
        "p_silenced": round(float(model.predict_silenced(one)[0]), 4),
        "interval_kind": iv["interval_kind"],
        "ood_widen": (round(float(iv["ood_widen"][0]), 3) if iv.get("ood_widen") is not None else None),
        "n_context_features_used": len(present),
        "cassette": cassette,
        "trained_on": {"n": model.meta.get("n"), "datasets": model.meta.get("datasets"),
                       "cell_types": model.meta.get("cell_types")},
        "scope_flags": ["learned_position_effect", "trained_conformal",
                        "single_context_supervision (mESC) - cross-cell-type transfer data-gated"],
        "provenance": "twin.position_effect, learned cassette x context + split-conformal (TRIP supervision)",
        "output_kind": "candidate",
    }


def conformal_heldout_coverage(oof: dict, alpha: float = 0.10, seed: int = 20260619) -> dict:
    """Conformal coverage: calibrate qhat on a RANDOM HALF of the chromosomes and evaluate coverage on
    the held-out half (exchangeable split). Evaluating on the calibration set itself would trivially report
    nominal coverage, this does not. This is the validation number; the shipped qhat uses all OOF residuals."""
    from pen_stack.wgenome.uncertainty import conformal_quantile
    y = np.asarray(oof["expression_true"], float)
    yhat = np.asarray(oof["expression_pred"], float)
    groups = np.asarray(oof["groups"])
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    rng.shuffle(uniq)
    calib_g = set(uniq[: len(uniq) // 2])
    cm = np.array([g in calib_g for g in groups])
    tm = ~cm
    qhat = conformal_quantile(np.abs(y[cm] - yhat[cm]), alpha)
    covered = (y[tm] >= yhat[tm] - qhat) & (y[tm] <= yhat[tm] + qhat)
    return {"nominal": round(1 - alpha, 3), "heldout_coverage": float(np.mean(covered)),
            "qhat_calib": float(qhat), "mean_width": float(2 * qhat),
            "n_calib": int(cm.sum()), "n_test": int(tm.sum()),
            "within_tol": bool(abs(float(np.mean(covered)) - (1 - alpha)) <= 0.03)}
