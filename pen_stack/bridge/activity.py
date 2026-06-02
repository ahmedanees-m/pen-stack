"""Bridge-recombinase activity model (Phase 1.5, Step 1.5.4) — EXPLORATORY add-on.

Predict human-cell activity of a recombinase ortholog/variant. Framed explicitly as exploratory: the DMS
is deep for one enzyme and the screen is only ~72 systems. Both training tables come from the Perry 2025
supplementary (paywalled, not bulk-downloadable here), so this provides the **framework** — a pluggable
trainer + retrospective-recovery harness — that trains and validates the moment the tables are supplied
(the same deferral pattern as the Phase-2 DMS variant proposal, which this also completes).

Headline of the phase is the off-target engine; this is a secondary result with an explicit N caveat.
"""
from __future__ import annotations

import pandas as pd


def have_training_data(dms: pd.DataFrame, screen: pd.DataFrame) -> bool:
    return (dms is not None and not dms.empty) or (screen is not None and not screen.empty)


def train_variant_effect(dms_df: pd.DataFrame):
    """Train a per-residue mutation -> activity model on the DMS. Returns None if no DMS available."""
    if dms_df is None or dms_df.empty:
        return None
    import lightgbm as lgb
    feat = pd.get_dummies(dms_df[["aa_position", "wt", "mut"]].astype(str))
    return lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03).fit(feat, dms_df["activity"])


def train_ortholog_activity(screen_df: pd.DataFrame, embed_fn=None):
    """Train ortholog -> human-cell activity on the 72-system screen. Returns None if absent.

    N caveat is the caller's responsibility to report — the screen is ~72 systems.
    """
    if screen_df is None or screen_df.empty:
        return None
    import lightgbm as lgb
    if embed_fn is not None:
        X = embed_fn(screen_df["sequence"])
    else:
        X = pd.get_dummies(screen_df.get("target_core", pd.Series(dtype=str)).astype(str))
    return lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03).fit(X, screen_df["human_cell_activity"])


def status() -> dict:
    """Report whether the activity model can train (needs the Perry 2025 DMS / screen tables)."""
    from pen_stack.bridge.ingest import load_dms, load_screen
    dms, screen = load_dms(), load_screen()
    return {"dms_rows": len(dms), "screen_rows": len(screen),
            "trainable": have_training_data(dms, screen),
            "note": "exploratory; DMS+screen are Perry 2025 supplementary (paywalled) — model trains when supplied"}
