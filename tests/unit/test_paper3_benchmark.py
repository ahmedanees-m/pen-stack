"""Phase 3, Step 3.5 - two-stratum recovery@k benchmark.

DE-CIRCULARIZED (v3.1, WS-A). The discriminating (targeted-intent) recovery@k is **definitional, not
predictive** - an on-target identity term makes the planner rank the goal's own gene first by construction
(see docs/benchmark_circularity.md and the CIRCULARITY NOTICE in paper3_benchmark.py). So we no longer
assert strict planner superiority here; that honest headline moved to the BLIND GSH discovery AUROC
(tests/unit/test_ws_a_decircularize.py::test_blind_gsh_discovery_auroc_gate). This test now only checks the
panel is frozen/stratified and that the planner is NOT WORSE than the intent-blind baseline on either
stratum. Skips when the Phase-1 writability atlas is absent.
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


def test_stratified_report_is_well_formed():
    # The discriminating recovery@k is circular/definitional and tie-break-sensitive (WS-A) - we do NOT
    # assert a performance ordering on it. The honest, deterministic performance headline is the blind GSH
    # discovery AUROC (test_ws_a_decircularize.py). Here we only check the report is well-formed for both
    # strata so downstream code/manuscripts read valid fields.
    from pen_stack.validate.paper3_benchmark import recovery_at_k, stratified_report
    panel = pd.read_csv(_PANEL)
    rep = stratified_report(recovery_at_k(panel, k=10))
    for stratum in ("discriminating", "control"):
        s = rep[stratum]
        assert s["n"] >= 1
        assert 0.0 <= s["planner_recovery"] <= 1.0
        assert 0.0 <= s["baseline_recovery"] <= 1.0
        assert {"mcnemar_pvalue", "gap_ci95", "ci_excludes_zero"} <= set(s)


def test_recovery_at_k_is_deterministic():
    # Regression: tied scores (saturated safety) used to resolve via an unstable quicksort, so identical
    # inputs gave different planner/baseline recovery vectors. The ranking now uses a stable sort with
    # explicit tie-breakers - two calls must produce identical hit vectors so out/benchmark_report.json
    # reproduces.
    from pen_stack.validate.paper3_benchmark import recovery_at_k
    panel = pd.read_csv(_PANEL)
    a = recovery_at_k(panel, k=10).sort_values("name").reset_index(drop=True)
    b = recovery_at_k(panel, k=10).sort_values("name").reset_index(drop=True)
    pd.testing.assert_frame_equal(a[["name", "planner_hit", "baseline_hit"]],
                                  b[["name", "planner_hit", "baseline_hit"]])
