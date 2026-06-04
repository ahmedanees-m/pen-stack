"""v3.1 WS-A - de-circularized benchmark validators.

Skip the data-dependent checks when the Phase-1 writability atlas is absent (CI). The intent-specification
and writer-recovery logic that needs only committed data runs always.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"


def test_writer_recovery_beats_prevalence():
    # uses only committed data (writer_panel.csv + atlas.parquet)
    from pen_stack.validate.writer_recovery import run
    r = run()
    assert r["n_families"] >= 3 and r["n_entries"] >= 8
    assert r["beats_prevalence"] is True
    assert r["recovery_at_1"] > r["prevalence_baseline_at_1"]


@pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")
def test_blind_gsh_discovery_auroc_gate():
    from pen_stack.validate.blind_gsh_discovery import run
    r = run()
    assert r["acceptance"]["PRIMARY_auroc_ge_0.70"] is True       # honest non-circular headline
    assert r["auroc_writability"] > r["auroc_safety_baseline"]


@pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")
def test_intent_specification_is_not_predictive():
    from pen_stack.validate.intent_specification import run
    r = run()
    # this is a correctness table, NOT a recovery metric - assert the framing is preserved
    assert r["all_correct"] is True
    assert "specification-compliance" in r["what_this_is"]
    assert "NOT a predictive" in r["what_this_is"]
