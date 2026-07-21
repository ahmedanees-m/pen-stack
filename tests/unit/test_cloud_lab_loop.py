"""Closed-loop unit tests: the cloud-lab connector (safety-gated), the SDL-brain benchmark,
and the validation-campaign engine. The biosecurity gate runs before any export; experiments are candidates."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pen_stack.active.brains import benchmark
from pen_stack.active.campaign import design_campaign, write_campaign_spec
from pen_stack.build.cloudlab import ingest_readout, submit_gated

_BENIGN = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "installed_att": True, "cargo_function": "insert a GFP reporter at the AAVS1 safe-harbour locus"}
_HAZARD = {"write_type": "insertion", "gene": "AAVS1", "cargo_bp": 2000, "cell_type": "hek293t",
           "cargo_function": "express active ricin toxin A chain for cytotoxicity"}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


def test_cloudlab_endpoint_422s_on_unknown_provider_not_500():
    """Regression (tester): POST /cloudlab with a provider outside the wired set returned an unhandled 500
    (submit_gated caught only the safety refusal, so submit()'s CloudLabError propagated). It must be a 422; a
    null/empty/missing provider falls back gracefully to the wired mock path (200 for a benign design)."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from pen_stack.server.api import app
    c = TestClient(app)
    bad = c.post("/cloudlab", json={"design": _BENIGN, "provider": "opentrons"})
    assert bad.status_code == 422 and "provider" in bad.json()["detail"].lower()
    for prov in (None, "", "mock"):
        body = {"design": _BENIGN} if prov == "mock" else {"design": _BENIGN, "provider": prov}
        assert c.post("/cloudlab", json=body).status_code == 200, prov


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
        assert "expression-validation campaign" in text.lower() and "calibrate_axis" in text
        assert "Level 3" in text  # autonomy framing present


def test_loop_bench_gates_pass():
    from benchmarks.loop.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["cloudlab_biosecurity"]["hazard_blocked"] is True
    assert r["cloudlab_biosecurity"]["cleared_design_submits_mock"] is True
    assert r["validation_campaign"]["targets_calibrate_axis"] is True
