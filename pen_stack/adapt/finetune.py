"""WS-F2(b) - OPTIONAL light fine-tuning: a LightGBM head on the user's features.

This is the heavier, opt-in path (the default WS-F adaptation is isotonic recalibration, which is far more
robust on small private datasets). It trains a small LightGBM classifier on the user's features+labels - or
continues training from a released booster via `init_model` - and is subject to the SAME validation gate:
it activates only if it beats the released model on the held-out split. Small-data overfitting is mitigated
(not eliminated) by the gate, shallow trees, and strong regularization.
"""
from __future__ import annotations

import numpy as np


def finetune_head(X, y, init_model=None, seed: int = 0, n_estimators: int = 100):
    """Train (or continue-train) a small, regularized LightGBM head. Returns the fitted model."""
    import lightgbm as lgb
    X, y = np.asarray(X, float), np.asarray(y, float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    model = lgb.LGBMClassifier(
        n_estimators=n_estimators, num_leaves=15, max_depth=4, learning_rate=0.05,
        min_child_samples=20, reg_lambda=1.0, subsample=0.8, colsample_bytree=0.8,
        random_state=seed, verbose=-1)
    model.fit(X, y.astype(int), init_model=init_model)
    return model


def predict_proba(model, X):
    import numpy as np
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    return model.predict_proba(X)[:, 1]
