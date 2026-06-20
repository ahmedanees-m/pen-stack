"""Calibrated uncertainty for the writable-genome heads (Phase 3.2, WS-UQ / UQ1).

Split / CV+ conformal *wrappers* around the EXISTING LightGBM heads (safety, durability-silenced
classification; durability-expression regression). Nothing is retrained here - we take a head's
out-of-fold (or held-out) predictions, learn a nonconformity quantile on a calibration set, and turn
point scores into:

  * regression -> prediction INTERVALS at a nominal coverage (durability expression);
  * classification -> calibrated prediction SETS + a coverage guarantee (safety, silenced).

Why conformal (not just isotonic): conformal gives a *distribution-free, finite-sample* coverage
guarantee - "the 90% interval covers the truth >= 90% of the time" - which is exactly the trust claim
v3.2 makes. The guarantee is **marginal** (population-level), not conditional; small calibration N (the
GSH/TRIP gold sets are small) yields **wide** intervals - that width is a reported output, reported with N,
never hidden. When marginal coverage fails under the chromosome-grouped distribution shift we fall back to
**group / Mondrian (class- or group-conditional) conformal** and report the gap rather than relax the target.

Design: model-agnostic - the calibrators take arrays of (prediction, truth), so the same code calibrates a
synthetic head in a unit test and the real OOF predictions on the VM. Reuses ``adapt.report`` for ECE /
reliability so there is one calibration vocabulary across the stack.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pen_stack.adapt.report import _auroc, _ece


# --------------------------------------------------------------------------------------------------
# finite-sample conformal quantile
# --------------------------------------------------------------------------------------------------
def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """The conformal (1-alpha) quantile of calibration nonconformity ``scores`` with the finite-sample
    correction: the rank is ceil((n+1)(1-alpha)) / n. Returns +inf when the correction exceeds n (too few
    calibration points to guarantee the requested coverage - a 'cannot certify' rather than a
    falsely tight bound)."""
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    if n == 0:
        return float("inf")
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        return float("inf") # cannot certify this coverage at this N
    return float(s[k - 1])


# --------------------------------------------------------------------------------------------------
# regression: normalized-residual conformal -> prediction intervals
# --------------------------------------------------------------------------------------------------
@dataclass
class ConformalRegressor:
    """Split/CV conformal for a regression head (durability expression).

    Nonconformity = ``|y - yhat| / sigma`` (normalized absolute residual; ``sigma`` is an optional
    per-point spread estimate, e.g. a quantile-spread model - defaults to 1.0, i.e. plain absolute
    residual). ``calibrate`` stores the conformal quantile ``qhat``; ``interval`` returns a symmetric
    band ``yhat +/- qhat * sigma``. With ``groups`` the quantile is computed per group (Mondrian /
    group-conformal) for conditional coverage under the chromosome-grouped split.
    """
    alpha: float = 0.10
    qhat: float = float("nan")
    qhat_by_group: dict = field(default_factory=dict)
    n_cal: int = 0

    def calibrate(self, y_true, y_pred, sigma=None, groups=None) -> "ConformalRegressor":
        y_true = np.asarray(y_true, float)
        y_pred = np.asarray(y_pred, float)
        sigma = np.ones_like(y_true) if sigma is None else np.asarray(sigma, float)
        sigma = np.where(sigma <= 0, 1e-9, sigma)
        scores = np.abs(y_true - y_pred) / sigma
        self.n_cal = int(len(scores))
        self.qhat = conformal_quantile(scores, self.alpha)
        if groups is not None:
            groups = np.asarray(groups)
            self.qhat_by_group = {
                str(g): conformal_quantile(scores[groups == g], self.alpha)
                for g in np.unique(groups)
            }
        return self

    def _q(self, group=None) -> float:
        if group is not None and self.qhat_by_group:
            return self.qhat_by_group.get(str(group), self.qhat)
        return self.qhat

    def interval(self, y_pred, sigma=None, group=None):
        y_pred = np.asarray(y_pred, float)
        sigma = np.ones_like(y_pred) if sigma is None else np.asarray(sigma, float)
        half = self._q(group) * sigma
        return y_pred - half, y_pred + half

    def coverage(self, y_true, y_pred, sigma=None, group=None) -> dict:
        y_true = np.asarray(y_true, float)
        lo, hi = self.interval(y_pred, sigma, group)
        covered = (y_true >= lo) & (y_true <= hi)
        width = hi - lo
        return {"nominal": 1 - self.alpha, "empirical_coverage": float(np.mean(covered)),
                "mean_width": float(np.mean(width)), "median_width": float(np.median(width)),
                "n": int(len(y_true)), "qhat": self._q(group),
                "within_tol": bool(abs(np.mean(covered) - (1 - self.alpha)) <= 0.03)}


# --------------------------------------------------------------------------------------------------
# classification: APS conformal -> calibrated prediction sets
# --------------------------------------------------------------------------------------------------
@dataclass
class ConformalClassifier:
    """Adaptive-Prediction-Set (APS) conformal for a binary head (safety genotoxic / durability silenced).

    APS nonconformity (Romano et al. 2020): for a calibration point, sort class probabilities descending
    and accumulate until the TRUE class is reached - that cumulative mass is the score. ``qhat`` is the
    conformal (1-alpha) quantile of those scores. A test prediction set adds classes from the top until the
    cumulative probability reaches ``qhat``, guaranteeing the set contains the truth with prob >= 1-alpha.
    With ``mondrian=True`` the quantile is computed per true class (class-conditional coverage) - the
    the choice under class imbalance (genotoxic sites are rare).

    Binary classes are 0/1; ``p1`` is P(class=1). Also exposes the set as one of {}, {0}, {1}, {0,1} and a
    simple calibrated confidence (1 - alpha when the set is a singleton, lower when ambiguous/empty).
    """
    alpha: float = 0.10
    mondrian: bool = True
    qhat: float = float("nan")
    qhat_by_class: dict = field(default_factory=dict)
    n_cal: int = 0

    @staticmethod
    def _aps_score(p1: float, y: int) -> float:
        p = [(1 - p1, 0), (p1, 1)]
        p.sort(reverse=True) # descending probability
        cum = 0.0
        for prob, cls in p:
            cum += prob
            if cls == y:
                return cum
        return cum

    def calibrate(self, y_true, p1) -> "ConformalClassifier":
        y_true = np.asarray(y_true, int)
        p1 = np.asarray(p1, float)
        scores = np.array([self._aps_score(pp, yy) for pp, yy in zip(p1, y_true)])
        self.n_cal = int(len(scores))
        self.qhat = conformal_quantile(scores, self.alpha)
        if self.mondrian:
            self.qhat_by_class = {
                int(c): conformal_quantile(scores[y_true == c], self.alpha)
                for c in np.unique(y_true)
            }
        return self

    def _q(self, cls: int) -> float:
        if self.mondrian and self.qhat_by_class:
            return self.qhat_by_class.get(int(cls), self.qhat)
        return self.qhat

    def predict_set(self, p1: float) -> set:
        """Smallest top-down set whose cumulative probability reaches the (class-appropriate) qhat."""
        p = [(1 - float(p1), 0), (float(p1), 1)]
        p.sort(reverse=True)
        out, cum = set(), 0.0
        for prob, cls in p:
            out.add(cls)
            cum += prob
            if cum >= self._q(cls):
                break
        return out

    def coverage(self, y_true, p1) -> dict:
        y_true = np.asarray(y_true, int)
        p1 = np.asarray(p1, float)
        sets = [self.predict_set(pp) for pp in p1]
        covered = np.array([yy in s for s, yy in zip(sets, y_true)])
        sizes = np.array([len(s) for s in sets])
        per_class = {int(c): float(np.mean(covered[y_true == c]))
                     for c in np.unique(y_true)} if self.mondrian else {}
        biny = y_true if set(np.unique(y_true)) <= {0, 1} else (y_true >= 0.5).astype(int)
        return {"nominal": 1 - self.alpha, "empirical_coverage": float(np.mean(covered)),
                "per_class_coverage": per_class, "mean_set_size": float(np.mean(sizes)),
                "singleton_rate": float(np.mean(sizes == 1)), "n": int(len(y_true)),
                "ece": _ece(p1, biny), "auroc": _auroc(list(p1), list(biny)),
                "within_tol": bool(abs(np.mean(covered) - (1 - self.alpha)) <= 0.03)}


# --------------------------------------------------------------------------------------------------
# reliability diagram (for figures / the model card)
# --------------------------------------------------------------------------------------------------
def reliability_curve(p1, y_true, n_bins: int = 10) -> dict:
    """Binned (mean predicted prob, empirical frequency, count) - the reliability diagram data + ECE."""
    p1 = np.asarray(p1, float)
    y = np.asarray(y_true, float)
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    for i in range(n_bins):
        hi_incl = i == n_bins - 1
        m = (p1 >= edges[i]) & (p1 <= edges[i + 1] if hi_incl else p1 < edges[i + 1])
        if m.sum():
            rows.append({"bin_lo": float(edges[i]), "bin_hi": float(edges[i + 1]),
                         "mean_pred": float(p1[m].mean()), "emp_freq": float(y[m].mean()),
                         "count": int(m.sum())})
    return {"bins": rows, "ece": _ece(p1, (y >= 0.5).astype(float)), "n": int(len(p1))}


# --------------------------------------------------------------------------------------------------
# bundle: calibrate every head + serialize the calibration artifact + model card
# --------------------------------------------------------------------------------------------------
class ConformalWrapper:
    """Bundles the per-head conformal calibrators and (de)serializes the calibration artifact.

    Holds an optional ``ood`` widening hook (a callable score-> multiplier from :mod:`wgenome.ood`) so an
    OOD query widens its interval / inflates its nonconformity. Persisted as plain JSON (qhat values + N +
    nominal) so a release ships the calibration, not the calibration data.
    """

    def __init__(self, alpha: float = 0.10):
        self.alpha = alpha
        self.reg: dict[str, ConformalRegressor] = {}
        self.clf: dict[str, ConformalClassifier] = {}
        self.meta: dict = {"alpha": alpha, "nominal_coverage": 1 - alpha}

    def add_regressor(self, name: str, r: ConformalRegressor) -> None:
        self.reg[name] = r

    def add_classifier(self, name: str, c: ConformalClassifier) -> None:
        self.clf[name] = c

    def to_dict(self) -> dict:
        return {"alpha": self.alpha, "nominal_coverage": 1 - self.alpha,
                "regressors": {k: {"qhat": v.qhat, "qhat_by_group": v.qhat_by_group, "n_cal": v.n_cal}
                               for k, v in self.reg.items()},
                "classifiers": {k: {"qhat": v.qhat, "qhat_by_class": v.qhat_by_class,
                                    "mondrian": v.mondrian, "n_cal": v.n_cal}
                                for k, v in self.clf.items()},
                "meta": self.meta}

    def save(self, path: str | Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str | Path) -> "ConformalWrapper":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        w = cls(alpha=d["alpha"])
        for k, v in d.get("regressors", {}).items():
            r = ConformalRegressor(alpha=d["alpha"], qhat=v["qhat"],
                                   qhat_by_group=v.get("qhat_by_group", {}), n_cal=v.get("n_cal", 0))
            w.reg[k] = r
        for k, v in d.get("classifiers", {}).items():
            c = ConformalClassifier(alpha=d["alpha"], mondrian=v.get("mondrian", True),
                                    qhat=v["qhat"],
                                    qhat_by_class={int(kk): vv for kk, vv in v.get("qhat_by_class", {}).items()},
                                    n_cal=v.get("n_cal", 0))
            w.clf[k] = c
        w.meta = d.get("meta", {})
        return w
