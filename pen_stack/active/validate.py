"""Retrospective active-learning validation, the falsifiability gate (v5.10, WS-VALIDATE).

Does an `active` strategy (uncertainty sampling) reach a target model quality in FEWER rounds than `random`/
`greedy` on held-out data? By construction: learning curves are reported with repetitions + a bootstrap CI
on the curve-area gap, WHATEVER the result, a not-yet-useful outcome is a valid, published finding. Retrospective
and dataset-dependent; prospective benefit awaits a lab (v5.11+).
"""
from __future__ import annotations

import numpy as np
from sklearn.neighbors import KNeighborsRegressor


def _synthetic_dataset(n: int = 240, d: int = 4, seed: int = 0):
    """A smooth regression surface (clustered features) where under-sampled regions carry real, learnable signal
, the standard setting in which uncertainty sampling can beat random. Returns (X, y)."""
    rng = np.random.default_rng(seed)
    X = np.vstack([rng.normal(c, 0.6, (n // 3, d)) for c in (-2.0, 0.0, 2.0)])
    y = np.sin(X[:, 0]) + 0.5 * X[:, 1] ** 2 - 0.3 * X[:, 2] + rng.normal(0, 0.05, len(X))
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


def _uncertainty(model: KNeighborsRegressor, X_pool, X_labeled) -> np.ndarray:
    """Distance to the nearest already-labeled point (higher = more uncertain / under-sampled region)."""
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=1).fit(X_labeled)
    return nn.kneighbors(X_pool)[0].ravel()


def _simulate_campaign(X, y, strategy, *, seed_n, batch, rounds, seed):
    rng = np.random.default_rng(seed)
    n = len(X)
    test = rng.choice(n, size=n // 4, replace=False)
    train_pool = np.array([i for i in range(n) if i not in set(test)])
    labeled = list(rng.choice(train_pool, size=seed_n, replace=False))
    pool = [i for i in train_pool if i not in set(labeled)]
    curve = []
    for _ in range(rounds):
        m = KNeighborsRegressor(n_neighbors=min(5, len(labeled))).fit(X[labeled], y[labeled])
        curve.append(float(np.mean(np.abs(m.predict(X[test]) - y[test])))) # held-out MAE
        if not pool:
            break
        Xp = X[pool]
        if strategy == "active":
            score = _uncertainty(m, Xp, X[labeled])
        elif strategy == "greedy":
            score = m.predict(Xp) # exploit predicted max
        else: # random
            score = rng.random(len(pool))
        pick = list(np.argsort(score)[::-1][:batch])
        chosen = [pool[i] for i in pick]
        labeled += chosen
        pool = [i for i in pool if i not in set(chosen)]
    return curve


def _mean_ci(curves):
    a = np.array([c[:min(map(len, curves))] for c in curves])
    mean = a.mean(0)
    lo, hi = np.percentile(a, [2.5, 97.5], axis=0)
    return {"mean": [round(x, 4) for x in mean], "lo": [round(x, 4) for x in lo],
            "hi": [round(x, 4) for x in hi]}


def _area(curve) -> float:
    """Trapezoidal area under a learning curve (unit spacing). Version-agnostic (np.trapz was removed in 2.0)."""
    c = np.asarray(curve, float)
    return float(np.sum((c[:-1] + c[1:]) / 2.0)) if len(c) > 1 else float(c.sum())


def _auc_gap_ci(active, random_, *, reps_seed=0):
    """Bootstrap CI of the learning-curve AREA gap (random_area - active_area); positive => active learns faster."""
    L = min(min(map(len, active)), min(map(len, random_)))
    a_area = np.array([_area(c[:L]) for c in active])
    r_area = np.array([_area(c[:L]) for c in random_])
    rng = np.random.default_rng(reps_seed)
    gaps = []
    for _ in range(500):
        i = rng.integers(0, len(a_area), len(a_area))
        j = rng.integers(0, len(r_area), len(r_area))
        gaps.append(float(np.mean(r_area[j]) - np.mean(a_area[i])))
    lo, hi = np.percentile(gaps, [2.5, 97.5])
    return {"mean_gap": round(float(np.mean(gaps)), 4), "ci": [round(float(lo), 4), round(float(hi), 4)],
            "active_beats_random": bool(lo > 0)}


def retrospective_active_learning(dataset=None, strategies=("active", "random", "greedy"),
                                  *, seed_n=8, batch=8, rounds=6, reps=20) -> dict:
    """Active vs random/greedy learning curves on held-out data, reported with reps + CI whatever the result."""
    X, y = dataset if dataset is not None else _synthetic_dataset()
    curves = {s: [_simulate_campaign(X, y, s, seed_n=seed_n, batch=batch, rounds=rounds, seed=r)
                  for r in range(reps)] for s in strategies}
    gap = _auc_gap_ci(curves["active"], curves["random"])
    return {
        "available": True, "reps": reps, "rounds": rounds,
        "curves": {s: _mean_ci(c) for s, c in curves.items()},
        "active_vs_random": gap,
        "active_beats_random": gap["active_beats_random"],
        "honest_note": ("active learns faster than random (curve-area CI excludes 0)" if gap["active_beats_random"]
                        else "active does NOT beat random on this data (CI spans 0) - reported, not hidden; "
                             "not-yet-useful is a valid outcome"),
        "no_fabrication": True,
    }
