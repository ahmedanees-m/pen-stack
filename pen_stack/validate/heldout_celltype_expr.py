"""Cross-cell-type transfer evaluation for Stage H (v6.7 PEN-EXPRESS, WS-X).

The HEADLINE transfer test: train on a subset of cell types, hold one out, predict it from its epigenome alone.
This is the characterization of *where* a position-effect model transfers. With a single available
position-effect cell type (mESC) it returns `data_gated`, NO transfer number is fabricated. It activates once
PatchMPRA / MPIRE / lentiMPRA / Leemans are fetched (the data-acquisition step, reported).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

from pen_stack.twin.data.position_effect import heldout_celltype_splits, load_position_effect
from pen_stack.twin.position_effect import PositionEffectModel


def heldout_celltype_transfer(df=None) -> dict:
    """Leave-one-cell-type-out transfer. Returns `data_gated` when <2 cell types are available."""
    df = df if df is not None else load_position_effect()
    splits = heldout_celltype_splits(df)
    if not splits:
        return {"status": "data_gated", "available_cell_types": sorted(df["cell_type"].unique()),
                "note": "leave-one-cell-type-out needs >=2 cell types; pending PatchMPRA/MPIRE/lentiMPRA/Leemans "
                        "acquisition. No transfer number is fabricated."}
    rows = {}
    for ct, tr, te in splits:
        model = PositionEffectModel().fit(df.iloc[tr])
        yhat = model.predict_expression(df.iloc[te])
        rho = float(spearmanr(yhat, df.iloc[te]["expression_raw"].to_numpy()).statistic)
        rows[ct] = {"rho": round(rho, 4), "n_test": int(len(te))}
    return {"status": "live", "by_heldout_cell_type": rows,
            "mean_transfer_rho": round(float(np.mean([r["rho"] for r in rows.values()])), 4)}
