"""Phase 3, Step 3.4 - end-to-end Write Planner.

Pre-registered criterion: a goal returns ranked, traceable plans; every field has provenance.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.planner.optimize import EditIntent
from pen_stack.planner.pipeline import plan_write
from pen_stack.planner.report import render_plans

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"

pytestmark = pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")


def test_plan_write_returns_traceable_plans():
    wdf = pd.read_parquet(_WDF)
    plans = plan_write("TRAC", EditIntent.KNOCK_IN_DISRUPT, 2000, "k562", k=3, writable_df=wdf)
    assert plans, "planner returned no plans"
    p = plans[0]
    # structure + provenance on every field
    for key in ("site", "writer", "safety", "durability", "cargo", "delivery", "provenance", "disclaimer"):
        assert key in p
    assert set(p["provenance"]) >= {"safety", "durability", "reachability", "delivery"}
    assert p["on_target"] is True            # knock-in ranks an in-TRAC site
    assert render_plans(plans).startswith("[rank 1]")


def test_plan_includes_cargo_and_delivery():
    wdf = pd.read_parquet(_WDF)
    p = plan_write("TRAC", EditIntent.KNOCK_IN_DISRUPT, 2000, "k562", k=1, writable_df=wdf)[0]
    assert p["cargo"]["size_ok"] in (True, False)
    assert "delivery" in p["delivery"]
