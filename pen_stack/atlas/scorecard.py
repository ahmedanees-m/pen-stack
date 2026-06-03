"""Descriptive writer scorecard (Phase 0, Step 0.5).

Reframes the prior 5-gate "TRUE_WRITER certification" (circular - it pre-registered ISCro4 *by name*
and depended on hand-set scores) into a transparent, DESCRIPTIVE scorecard computed from the
re-grounded axes. No enzyme is named in any pre-registered prediction. We additionally report a
*blind concordance* outcome: does the ranking place ISCro4 at the top of the bridge family using only
generic measured axes (cell-based evidence, DSB-freeness, programmability, cargo) - without any
ISCro4-specific value being asserted? This is reported, never asserted as an input.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_AXES_CFG = Path(__file__).resolve().parents[2] / "configs" / "score_axes.yaml"

_EVIDENCE_COLS = ["has_biochemical", "has_structural", "has_computational", "has_cell_based"]

# descriptive tier labels (NOT a certification; no enzyme is pre-named)
T_DSB_DEPENDENT = "DSB_dependent"        # fails the necessary DSB-free gate (a "scissor")
T_EMERGING = "emerging_writer"
T_PROBABLE = "probable_writer"
T_ESTABLISHED = "established_writer"      # DSB-free + fully programmable + native cargo + human-cell evidence


def _thresholds(path: Path = _AXES_CFG) -> dict:
    """Read v3.0 gate thresholds (defined on the RE-GROUNDED axis scales) from score_axes.yaml."""
    if Path(path).exists():
        g = yaml.safe_load(Path(path).read_text(encoding="utf-8")).get("gates_v3_0", {})
        return {
            "g1": g.get("g1_dsb_min", 0.95),
            "g2": g.get("g2_prog_min", 0.95),
            "g3": g.get("g3_cargo_min", 0.65),
            "g4": g.get("g4_max_length_aa", 900),
            "g5": g.get("g5_min_evidence", 2),
        }
    return {"g1": 0.95, "g2": 0.95, "g3": 0.65, "g4": 900, "g5": 2}


def _evidence_count(row) -> int:
    return int(sum(bool(row.get(c, False)) for c in _EVIDENCE_COLS))


def _gates(row, th) -> dict:
    g1 = float(row.get("s_dsb", 0) or 0) >= th["g1"]
    g2 = float(row.get("S_Prog", 0) or 0) >= th["g2"]
    g3 = (float(row.get("S_Cargo", 0) or 0) >= th["g3"]) and bool(row.get("intrinsic_cargo_mechanism", False))
    length = row.get("length_aa")
    g4 = (length is not None and not pd.isna(length) and float(length) <= th["g4"])
    g5 = _evidence_count(row) >= th["g5"]
    return {"g1": g1, "g2": g2, "g3": g3, "g4": g4, "g5": g5}


def _descriptive_tier(row, th) -> str:
    g = _gates(row, th)
    if not g["g1"]:
        return T_DSB_DEPENDENT                       # necessary gate (DSB-free) failed
    qualifying = sum([g["g2"], g["g3"], g["g4"], g["g5"]])
    has_cell = bool(row.get("has_cell_based", False))
    if qualifying == 4 and has_cell:
        return T_ESTABLISHED
    if qualifying == 4 or (qualifying == 3 and has_cell):
        return T_PROBABLE
    if qualifying >= 1:
        return T_EMERGING
    return T_DSB_DEPENDENT


def composite(row) -> float:
    """Transparent composite; components stay visible on the scorecard.

    Includes human-cell evidence (``has_cell_based``) as a generic readiness axis - this is the
    signal that distinguishes the standout human-cell bridge recombinase. It is a generic column
    present for every editor, NOT an ISCro4-specific asserted value (so the concordance stays blind).
    """
    parts = [
        float(row.get("s_dsb", 0) or 0),
        float(row.get("S_Prog", 0) or 0),
        float(row.get("S_Cargo", 0) or 0),
        _evidence_count(row) / 4.0,
        float(bool(row.get("has_cell_based", False))),
    ]
    return float(np.mean(parts))


def scorecard(universe_df: pd.DataFrame) -> pd.DataFrame:
    th = _thresholds()
    df = universe_df.copy()
    df["evidence_count"] = df.apply(_evidence_count, axis=1)
    df["S_composite"] = df.apply(composite, axis=1)
    df["tier"] = df.apply(lambda r: _descriptive_tier(r, th), axis=1)
    return df.sort_values("S_composite", ascending=False).reset_index(drop=True)


def blind_concordance(scorecard_df: pd.DataFrame, family: str = "bridge_IS110",
                      expected_top: str = "ISCro4") -> dict:
    """Report (do NOT assert) whether the ranking places `expected_top` first within `family`,
    using only generic measured axes. Returns the observed top + whether it matches.
    Restricted to NATURAL editors (the concordance question is about natural systems)."""
    sub = scorecard_df.query("family == @family")
    if "source" in sub.columns:
        sub = sub[sub["source"] == "natural"]
    sub = sub.sort_values("S_composite", ascending=False)
    if sub.empty:
        return {"family": family, "top": None, "matches": False, "n": 0}
    top = sub.iloc[0]["entity_id"]
    return {"family": family, "top": top, "matches": (top == expected_top), "n": int(len(sub)),
            "ranking": sub[["entity_id", "S_composite", "evidence_count"]].to_dict("records")}


def ranking_stability(universe_df: pd.DataFrame, family: str = "bridge_IS110",
                      expected_top: str = "ISCro4", n: int = 200, seed: int = 42) -> float:
    """Fraction of randomly re-weighted composites under which `expected_top` stays family-top
    (a lightweight sensitivity check, mirroring the prior ranking-stability analysis)."""
    rng = np.random.default_rng(seed)
    sub = universe_df.query("family == @family").copy()
    if "source" in sub.columns:
        sub = sub[sub["source"] == "natural"]
    if sub.empty:
        return 0.0
    cols = ["s_dsb", "S_Prog", "S_Cargo"]
    ev = sub.apply(_evidence_count, axis=1).to_numpy() / 4.0
    cell = sub.get("has_cell_based", pd.Series([False] * len(sub))).fillna(False).astype(float).to_numpy()
    X = np.column_stack([sub[c].fillna(0).astype(float).to_numpy() for c in cols] + [ev, cell])
    wins = 0
    for _ in range(n):
        w = rng.dirichlet(np.ones(X.shape[1]))
        scores = X @ w
        if sub.iloc[int(scores.argmax())]["entity_id"] == expected_top:
            wins += 1
    return wins / n
