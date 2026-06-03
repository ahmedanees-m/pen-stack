"""Phase 3, Step 3.5 - two-stratum recovery@k benchmark (paper-defining).

Pre-registered criterion: on the discriminating stratum the Planner beats the intent-blind baseline with
a bootstrap CI excluding zero; on the control stratum the Planner is not worse. Skips when the Phase-1
writability atlas is absent.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"
_PANEL = Path(__file__).resolve().parents[2] / "data" / "benchmark_panel.csv"

pytestmark = pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")


def test_panel_frozen_and_stratified():
    panel = pd.read_csv(_PANEL)
    assert set(panel["stratum"]) == {"control", "discriminating"}
    assert (panel["stratum"] == "discriminating").sum() >= 5
    assert panel["citation_doi"].notna().all()   # every panel write is cited


def test_discriminating_beats_baseline_ci_excludes_zero():
    from pen_stack.validate.paper3_benchmark import recovery_at_k, stratified_report
    panel = pd.read_csv(_PANEL)
    rec = recovery_at_k(panel, k=10)
    rep = stratified_report(rec)
    disc = rep["discriminating"]
    assert disc["planner_recovery"] > disc["baseline_recovery"]
    assert disc["ci_excludes_zero"] is True
    # control: planner not worse than baseline
    ctrl = rep["control"]
    assert ctrl["planner_recovery"] >= ctrl["baseline_recovery"] - 1e-9
