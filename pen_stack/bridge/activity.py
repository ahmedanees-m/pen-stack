"""Bridge-recombinase variant-effect, from the deep mutational scan (Phase 1.5, Step 1.5.4) - SECONDARY.

A pluggable trainer over the Perry 2025 DMS (Table S3). Used retrospectively it RECOVERS KNOWN
activity-enhancing mutants (N322P, H50K, R278M; see pen_stack/validate/paper4_real_validation.py),
completing the Phase-2 Step-2.4 DMS variant-proposal feature.

Scope, stated plainly: this is a useful catalogue feature that recovers KNOWN enhancers; it is NOT a novel
variant-design method. For GENERATING new variants the established engine is EVOLVEpro - when PEN-STACK
reaches generative variant design it should wrap EVOLVEpro rather than rebuild it. The 72-system ortholog
screen (Table S1) carries no per-system activity label, so it supports only the descriptive characterisation
in ortholog_screen.py (N ~72, exploratory). The headline of the phase is the off-target screening engine.
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

    N caveat is the caller's responsibility to report - the screen is ~72 systems.
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
            "note": "exploratory; DMS+screen are Perry 2025 supplementary (paywalled) - model trains when supplied"}
