"""Out-of-distribution / extrapolation detection (Phase 3.2, WS-UQ / UQ2).

A model's prediction is only as trustworthy as the resemblance of the query to what the model was trained
on. This detector scores how far a query sits from the training feature distribution and, when far,
**widens the conformal interval / lowers the confidence** (the hook into :mod:`wgenome.uncertainty`). It is
the difference between "grounded-confident" and "grounded-extrapolating" in the v3.2 epistemic taxonomy.

Methods (pick per data size):
  * ``mahalanobis`` (default) - distance to the training mean under the (shrunk) training covariance;
    natural for the low-dimensional chromatin/distance feature spaces here.
  * ``knn`` - mean distance to the k nearest training points (non-parametric; robust to non-Gaussianity).
  * ``isolation_forest`` - tree-based density (sklearn), for larger feature sets.

Honesty: OOD is defined **relative to the training data, not ground truth** - it flags "far from what I
have seen," never "wrong." The threshold is calibrated on a held-out in-distribution-vs-deliberately-OOD
construction (e.g. a held-out cell type or a sequence-divergent locus class) and the separation AUROC is
reported; it is a heuristic confidence signal, not a guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pen_stack.adapt.report import _auroc


@dataclass
class OODDetector:
    method: str = "mahalanobis"
    k: int = 10
    shrinkage: float = 1e-3                  # ridge on the covariance (numerical + small-N stability)
    # fitted state
    mean_: np.ndarray | None = None
    inv_cov_: np.ndarray | None = None
    train_: np.ndarray | None = None
    iforest_: object | None = None
    threshold_: float = float("nan")
    train_quantiles_: dict = field(default_factory=dict)

    # ---- fit -------------------------------------------------------------------------------------
    def fit(self, X_train) -> "OODDetector":
        X = np.asarray(X_train, float)
        X = np.nan_to_num(X, nan=0.0)
        self.mean_ = X.mean(axis=0)
        if self.method == "mahalanobis":
            cov = np.cov(X, rowvar=False)
            cov = np.atleast_2d(cov) + self.shrinkage * np.eye(X.shape[1])
            self.inv_cov_ = np.linalg.pinv(cov)
        elif self.method == "knn":
            self.train_ = X
            try:
                from scipy.spatial import cKDTree
                self._kdtree = cKDTree(X)                 # O(log n) queries instead of an O(n) row-loop
            except Exception:  # noqa: BLE001 - scipy absent -> fall back to the brute-force loop
                self._kdtree = None
        elif self.method == "isolation_forest":
            from sklearn.ensemble import IsolationForest
            self.iforest_ = IsolationForest(n_estimators=200, random_state=42).fit(X)
        else:
            raise ValueError(f"unknown OOD method: {self.method}")
        # store the in-distribution score distribution (for a default threshold + monotone widening)
        s = self.score(X)
        self.train_quantiles_ = {q: float(np.quantile(s, q)) for q in (0.5, 0.9, 0.95, 0.99)}
        self.threshold_ = self.train_quantiles_[0.95]      # default: 95th in-dist percentile
        return self

    # ---- score -----------------------------------------------------------------------------------
    def score(self, X) -> np.ndarray:
        """Higher = more out-of-distribution."""
        X = np.nan_to_num(np.asarray(X, float), nan=0.0)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if self.method == "mahalanobis":
            d = X - self.mean_
            m2 = np.einsum("ij,jk,ik->i", d, self.inv_cov_, d)
            return np.sqrt(np.clip(m2, 0, None))
        if self.method == "knn":
            kk = min(self.k, len(self.train_))
            if getattr(self, "_kdtree", None) is not None:
                d, _ = self._kdtree.query(X, k=kk)           # (n, kk) nearest-neighbour distances
                d = np.atleast_2d(d)
                return d.mean(axis=1)
            out = []
            for row in X:
                dist = np.sqrt(((self.train_ - row) ** 2).sum(axis=1))
                out.append(float(np.sort(dist)[:kk].mean()))
            return np.asarray(out)
        if self.method == "isolation_forest":
            return -self.iforest_.score_samples(X)         # higher = more anomalous
        raise ValueError(self.method)

    # ---- threshold calibration on a held-out in-dist vs OOD set ----------------------------------
    def calibrate_threshold(self, X_id, X_ood) -> dict:
        """Pick a threshold separating held-out in-distribution from deliberately-OOD queries and report
        the separation AUROC (acceptance: >= 0.75). Threshold = Youden-J-optimal point on the ROC."""
        s_id = self.score(X_id)
        s_ood = self.score(X_ood)
        scores = np.concatenate([s_id, s_ood])
        labels = np.concatenate([np.zeros(len(s_id)), np.ones(len(s_ood))])    # 1 = OOD
        auroc = _auroc(list(scores), list(labels))
        # Youden J over candidate thresholds (the unique scores), VECTORIZED via searchsorted so this is
        # O(n log n), not O(n^2) - the naive per-threshold mean loop is prohibitive at n in the thousands.
        thr = np.unique(scores)
        id_sorted, ood_sorted = np.sort(s_id), np.sort(s_ood)
        tpr = 1.0 - np.searchsorted(ood_sorted, thr, side="left") / len(ood_sorted)   # P(s_ood >= t)
        fpr = 1.0 - np.searchsorted(id_sorted, thr, side="left") / len(id_sorted)      # P(s_id  >= t)
        j = tpr - fpr
        best = int(np.argmax(j))
        best_t, best_j = float(thr[best]), float(j[best])
        self.threshold_ = best_t
        return {"auroc": auroc, "threshold": best_t, "youden_j": best_j,
                "n_id": int(len(s_id)), "n_ood": int(len(s_ood)),
                "separates": bool(auroc >= 0.75)}

    def is_ood(self, X) -> np.ndarray:
        return self.score(X) >= self.threshold_

    # ---- widening hook into the conformal interval -----------------------------------------------
    def widen_factor(self, X, cap: float = 3.0) -> np.ndarray:
        """Monotone interval-widening / confidence-deflation multiplier in [1, cap].

        1.0 at/below the in-distribution median; rises smoothly with the OOD score, saturating at ``cap``.
        Monotonicity is the UQ2 acceptance property: more OOD never narrows the interval.
        """
        s = self.score(X)
        lo = self.train_quantiles_.get(0.5, float(np.median(s)))
        hi = self.train_quantiles_.get(0.99, lo + 1.0)
        span = max(hi - lo, 1e-9)
        frac = np.clip((s - lo) / span, 0.0, 1.0)
        return 1.0 + frac * (cap - 1.0)

    def confidence(self, X) -> np.ndarray:
        """A 0-1 confidence that DECREASES monotonically with the OOD score (1 / widen_factor)."""
        return 1.0 / self.widen_factor(X)
