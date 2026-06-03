"""Phase 3, Step 3.1 - inverse-design optimiser with edit_intent.

Pre-registered criterion: edit_intent changes the ranking sensibly - an in-gene site ranks high for
knock_in_with_disruption and low for safe_harbour_insertion. Uses a synthetic candidate frame (offline)
plus, when present, the Phase-1 writability atlas for an end-to-end check.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.planner.optimize import EditIntent, plan, score_candidates

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"


def _synthetic():
    # two sites: one inside the target gene (on_target), one safe off-target
    return pd.DataFrame({
        "chrom": ["chr14", "chr14"],
        "bin": [100, 200],
        "safety": [0.6, 1.0],
        "p_durable": [0.8, 0.9],
        "reachable_tier1": ["bridge_IS110;Cas9;Cas12a", "bridge_IS110;Cas9;Cas12a"],
        "on_target": [True, False],
    })


def test_intent_flips_on_target_ranking():
    cands = _synthetic()
    ki = score_candidates(cands, EditIntent.KNOCK_IN_DISRUPT, cargo_bp=2000)
    sh = score_candidates(cands, EditIntent.SAFE_HARBOUR, cargo_bp=2000)
    # knock-in rewards the on-target site -> it ranks first; safe-harbour penalises it -> ranks last
    assert bool(ki.iloc[0]["on_target"]) is True
    assert bool(sh.iloc[0]["on_target"]) is False


def test_components_and_writer_retained():
    out = score_candidates(_synthetic(), EditIntent.HIGH_DURABILITY, cargo_bp=2000)
    for col in ("safety", "p_durable", "writer", "writer_activity", "score", "cargo_ok"):
        assert col in out.columns
    assert set(out["writer"]) <= {"bridge_IS110", "Cas9", "Cas12a"}


@pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")
def test_end_to_end_trac():
    wdf = pd.read_parquet(_WDF)
    ki = plan("TRAC", EditIntent.KNOCK_IN_DISRUPT, 2000, wdf, k=5)
    assert not ki.empty
    assert bool(ki.iloc[0]["on_target"])   # knock-in ranks an in-TRAC site at the top
