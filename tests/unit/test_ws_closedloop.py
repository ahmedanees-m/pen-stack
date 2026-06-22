"""WS-CLOSEDLOOP (v7.0 Stage J) unit tests: the cloud-lab connector (safety-gated), the SDL-brain benchmark,
and the validation-campaign engine. The biosecurity gate runs before any export; experiments are candidates."""
from __future__ import annotations

import tempfile
from pathlib import Path

from pen_stack.active.brains import benchmark
from pen_stack.active.campaign import design_campaign, write_campaign_spec
from pen_stack.build.cloudlab import ingest_readout, submit_gated

_BENIGN = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "installed_att": True, "cargo_function": "insert a GFP reporter at the AAVS1 safe-harbour locus"}
_HAZARD = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "cargo_function": "express active ricin toxin A chain for cytotoxicity"}


def test_cloudlab_submits_cleared_and_blocks_hazard():
    cleared = submit_gated(_BENIGN, {"round": 1}, actor="test")
    assert cleared.get("status") == "submitted_mock" and not cleared.get("blocked")
    assert cleared["job_id"].startswith("mock-") and cleared["dry_run"] is True
    blocked = submit_gated(_HAZARD, {"round": 1}, actor="test")
    assert blocked["blocked"] is True and "submitted" not in blocked.get("status", "")
    assert "safety" in blocked["reason"].lower()  # the biosecurity gate fired; no protocol emitted


def test_cloudlab_ingest_is_human_gated():
    held = ingest_readout("mock-123", {"expression": 0.8})
    assert held["admitted"] is False and held["held"] is True  # Level-3: a human must admit
    admitted = ingest_readout("mock-123", {"expression": 0.8}, admitted_by="curator")
    assert admitted["admitted"] is True and admitted["human_in_control"] is True


def test_brain_benchmark_reports_verbatim_and_cites():
    b = benchmark(reps=12, rounds=5)
    assert "BayBE" in b["references"] and "Atlas" in b["references"]
    assert isinstance(b["eig_beats_random"], bool)  # falsifiable, reported either way
    assert "mean_gap" in b["eig_vs_random"] and b["gate_pass"] is True


def test_validation_campaign_targets_calibrate_axis():
    c = design_campaign(reps=12, rounds=5)
    assert c["n_candidates"] > 0 and c["batch_size"] > 0
    assert "calibrate_axis" in c["target_gate"]["gate"]
    assert c["cloud_lab_executable"] is True and c["autonomy_level"] == 3
    assert isinstance(c["eig_beats_random"], bool)  # reported verbatim (a negative is valid)


def test_campaign_spec_is_generated():
    with tempfile.TemporaryDirectory() as d:
        p = write_campaign_spec(Path(d) / "campaign.md")
        text = Path(p).read_text(encoding="utf-8")
        assert "expression-validation campaign" in text and "calibrate_axis" in text
        assert "Level 3" in text  # autonomy framing present


def test_loop_bench_gates_pass():
    from benchmarks.loop.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["cloudlab_biosecurity"]["hazard_blocked"] is True
    assert r["cloudlab_biosecurity"]["cleared_design_submits_mock"] is True
    assert r["validation_campaign"]["targets_calibrate_axis"] is True
