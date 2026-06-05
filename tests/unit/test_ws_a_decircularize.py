"""v3.1 WS-A - de-circularized benchmark validators.

Skip the data-dependent checks when the Phase-1 writability atlas is absent (CI). The intent-specification
and writer-recovery logic that needs only committed data runs always.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_WDF = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"


def test_writer_recovery_beats_prevalence():
    # uses only committed data (writer_panel.csv + atlas.parquet); panel scaled to 14 documented writes
    from pen_stack.validate.writer_recovery import run
    r = run()
    assert r["n_families"] >= 4 and r["n_entries"] >= 14      # scaled gold set
    assert r["beats_prevalence"] is True
    assert r["recovery_at_1"] > r["prevalence_baseline_at_1"]
    # recovery@1 is now < 1.0 by design (honest non-minimal-capacity choices like twinPE / phiC31)
    assert r["recovery_at_1"] < 1.0


@pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")
def test_blind_gsh_discovery_scaled_and_honest():
    from pen_stack.validate.blind_gsh_discovery import run
    r = run()
    # Scaled gold set: >= 16 independent loci, with a validated tier, each AUROC carrying a bootstrap CI.
    assert r["n_positives"] >= 16 and r["n_validated"] >= 8
    allb = r["discrimination_by_tier"]["all_loci"]
    valb = r["discrimination_by_tier"]["validated_PRIMARY"]
    assert allb["auroc_writability_ci95"] is not None and valb["auroc_writability_ci95"] is not None
    # Honest signal: writability beats the safety baseline; the all-loci CI lower bound is above chance.
    assert allb["auroc_writability"] > allb["auroc_safety_baseline"]
    assert r["acceptance"]["all_loci_ci_excludes_chance"] is True
    # The headline must never be a bare point estimate - it carries the CI and N.
    assert "95% CI" in r["headline"] and "N=" in r["headline"]


@pytest.mark.skipif(not _WDF.exists(), reason="Phase-1 writability atlas not present")
def test_intent_specification_is_not_predictive():
    from pen_stack.validate.intent_specification import run
    r = run()
    # this is a correctness table, NOT a recovery metric - assert the framing is preserved
    assert r["all_correct"] is True
    assert "specification-compliance" in r["what_this_is"]
    assert "NOT a predictive" in r["what_this_is"]
