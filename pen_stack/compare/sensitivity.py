"""Sensitivity analysis — 18,000 threshold combinations per entity.

Replaces fabricated-sigma bootstrap. Each entity is certified under every
combination of the pre-registered sensitivity grid and a robustness fraction
is reported: fraction of combinations that agree with the modal tier.
"""

import itertools
from collections import Counter

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from pen_stack.compare.core.certify import certify

SENSITIVITY_GRID = {
    "g1_threshold": np.round(np.arange(0.85, 1.00, 0.01), 2).tolist(),  # 15 values
    "g2_threshold": np.round(np.arange(0.85, 1.00, 0.01), 2).tolist(),  # 15 values
    "g3_threshold": np.round(np.arange(0.80, 0.96, 0.01), 2).tolist(),  # 16 values
    "g4_size_max": [600, 750, 900, 1050, 1200],  #  5 values
}
# 15 × 15 × 16 × 5 = 18,000 combinations per entity


def sensitivity_for_entity(row: dict, grid: dict = SENSITIVITY_GRID) -> dict:
    """Run 18,000 certifications for one entity; return robustness metrics."""
    combos = list(itertools.product(*grid.values()))
    keys = list(grid.keys())

    tiers = []
    for combo in combos:
        c = dict(zip(keys, combo))
        result = certify(
            editor_id=row["entity_id"],
            s_dsb=row["s_dsb"],
            s_prog=row["s_prog"],
            s_cargo=row["s_cargo"],
            length_aa=row["length_aa_int"],
            evidence_sources=row["evidence_sources"],
            intrinsic_cargo_mechanism=bool(row["intrinsic_cargo_mechanism"]),
            split_aav_eligible=row["split_aav_eligible"],
            g1_threshold=c["g1_threshold"],
            g2_threshold=c["g2_threshold"],
            g3_threshold=c["g3_threshold"],
            g4_size_max=c["g4_size_max"],
        )
        tiers.append(result.tier)

    counts = Counter(tiers)
    modal, modal_n = counts.most_common(1)[0]
    total = len(tiers)

    return {
        "entity_id": row["entity_id"],
        "source": row["source"],
        "default_tier": row["default_tier"],
        "modal_tier": modal,
        "robustness": round(modal_n / total, 4),
        "n_combos": total,
        "tier_dist": dict(counts),
        "is_robust": (modal_n / total) >= 0.80,
        "is_boundary": (modal_n / total) < 0.50,
    }


def build_sensitivity_rows(universe: pd.DataFrame, scorecard: pd.DataFrame) -> list[dict]:
    """Merge universe + scorecard into flat dicts ready for sensitivity_for_entity."""
    # Rename has_cell_based from universe to avoid column-name collision with the
    # scorecard parquet (which also has a has_cell_based column from certify output).
    # Without renaming, pandas suffixes both to _x/_y and r.get("has_cell_based")
    # silently returns NaN, dropping "cell_based" from every evidence list.
    universe_slice = universe[
        [
            "entity_id",
            "s_dsb",
            "s_prog",
            "s_cargo",
            "length_aa",
            "intrinsic_cargo_mechanism",
            "has_biochemical",
            "has_structural",
            "has_computational",
            "has_cell_based",
        ]
    ].rename(columns={"has_cell_based": "has_cell_based_ev"})

    merged = scorecard.merge(universe_slice, on="entity_id", how="left")

    rows = []
    for _, r in merged.iterrows():
        length_aa_int = int(r["length_aa"]) if pd.notna(r["length_aa"]) else 450
        evidence = [
            src
            for src, col in [
                ("biochemical", "has_biochemical"),
                ("structural", "has_structural"),
                ("computational", "has_computational"),
                ("cell_based", "has_cell_based_ev"),
            ]
            if r.get(col)
        ]
        rows.append(
            {
                "entity_id": r["entity_id"],
                "source": r["source"],
                "default_tier": r["tier"],
                "s_dsb": float(r["s_dsb"]) if pd.notna(r["s_dsb"]) else 0.0,
                "s_prog": float(r["s_prog"]) if pd.notna(r["s_prog"]) else 0.0,
                "s_cargo": float(r["s_cargo"]) if pd.notna(r["s_cargo"]) else 0.0,
                "length_aa_int": length_aa_int,
                "split_aav_eligible": length_aa_int <= 1500,
                "intrinsic_cargo_mechanism": bool(r["intrinsic_cargo_mechanism"]),
                "evidence_sources": evidence,
            }
        )
    return rows


def run_sensitivity_parallel(
    universe: pd.DataFrame,
    scorecard: pd.DataFrame,
    n_jobs: int = 24,
    grid: dict = SENSITIVITY_GRID,
) -> pd.DataFrame:
    """Run sensitivity analysis in parallel; return results DataFrame."""
    rows = build_sensitivity_rows(universe, scorecard)
    results = Parallel(n_jobs=n_jobs, verbose=5)(
        delayed(sensitivity_for_entity)(r, grid) for r in rows
    )
    return pd.DataFrame(results)
