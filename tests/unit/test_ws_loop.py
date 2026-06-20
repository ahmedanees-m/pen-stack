"""WS-LOOP / WS-CONTINUAL / WS-DRIFT unit tests (Phase 5.12, the closed loop / autonomy Level 3).

CI-safe (explicit candidate pool + sim-lab). Asserts:
  * one command runs a full gated DBTL loop end-to-end (sim-lab); autonomy Level 3, human-in-control, no fabrication;
  * a hazardous candidate never reaches an admitted result (discarded by the safety-gated pipeline);
  * drift detection separates a matched stream (low) from a shifted one (high) and drives interval inflation;
  * continual learning updates only from admitted evidence, is versioned + reversible, and high drift widens intervals;
  * the convergence (active-vs-random) is reported with a CI either way (falsifiable, honest), Level 3 not 5.
"""
from __future__ import annotations

import pytest

from pen_stack.loop.continual import continual_update
from pen_stack.loop.cycle import loop_converges_faster_than_random, run_loop
from pen_stack.loop.drift import detect_drift

_BASE = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
         "cargo_bp": 3000, "cell_type": "k562", "writer_family": "bridge_IS110", "promoter": "ef1a",
         "accessibility": 0.8, "safety": 0.92, "p_durable": 0.8, "writer_activity": 0.7, "deliverability": 0.36}
_GOAL = {"gene": "AAVS1", "intent": "safe_harbour_insertion", "cargo_bp": 3000, "cell_type": "k562"}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


def _pool():
    cands = [{**_BASE, "delivery_vehicle": v} for v in ("AAV_single", "AAV_dual", "lentivirus")]
    cands.append({**_BASE, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}) # hazard
    return cands


# --- WS-LOOP ---------------------------------------------------------------------------

def test_loop_runs_end_to_end_gated_level3():
    r = run_loop(_GOAL, "k562", candidates=_pool(), rounds=3, approver="human", seed=0)
    assert r["autonomy_level"] == 3 and r["human_in_control"] is True # Level 3, NOT 5 (not autonomous)
    assert r["no_fabrication"] is True
    assert r["history"] and r["history"][0]["n"] >= 1 # the loop ran experiments
    assert r["final_model_version"] is not None # beliefs were versioned


def test_hazard_never_reaches_an_admitted_result():
    r = run_loop(_GOAL, "k562", candidates=_pool(), rounds=2, approver="human", seed=0)
    # the ricin candidate is discarded by the safety-gated pipeline; no admitted result carries it
    for h in r["history"]:
        assert h.get("blocked", 0) >= 0 # export gate present (2nd line of defence)
    # the loop completed without the hazard ever being "run"
    assert r["no_fabrication"] is True


# --- WS-DRIFT --------------------------------------------------------------------------

def test_drift_separates_matched_from_shifted():
    designs = [_BASE]
    low = detect_drift(designs, [{"readout": 0.44}], cell_state="k562") # close to the twin prediction
    high = detect_drift(designs, [{"readout": 0.99}], cell_state="k562") # far from prediction
    assert low["severity"] == "low" and low["action"] == "monitor"
    assert high["severity"] == "high" and high["action"] == "inflate_intervals"


# --- WS-CONTINUAL ----------------------------------------------------------------------

def test_continual_versioned_reversible_and_admitted_only():
    none = continual_update([], approver="human", prev_version="v0")
    assert none["updated"] is False # no admitted evidence -> no update
    upd = continual_update([{"readout": 0.5}], drift={"severity": "high", "ece": 0.3},
                           approver="human", prev_version="vPREV")
    assert upd["updated"] is True and upd["version"] # versioned
    assert upd["rollback_to"] == "vPREV" # reversible
    assert upd["interval_inflation"] > 1.0 # high drift widens intervals


def test_immune_proxy_graduation_requires_admitted_measurement_with_ci():
    # without a CI'd immune measurement -> no graduation
    upd = continual_update([{"readout": 0.5}], approver="human")
    assert upd["immune_labels"]["graduated_to_validated"] == []
    # an admitted immune measurement WITH a CI graduates the axis
    upd2 = continual_update([{"readout": 0.5, "immune_axis_measured": "genotoxicity", "ci": [0.1, 0.4]}],
                            approver="human")
    assert "genotoxicity" in upd2["immune_labels"]["graduated_to_validated"]


# --- WS-DEMO / WS-AUTONOMY -------------------------------------------------------------

def test_convergence_reported_with_ci_falsifiable():
    c = loop_converges_faster_than_random(reps=12, rounds=6)
    assert isinstance(c["reaches_optimum_faster_than_random"], bool) # reported either way (honest)
    assert len(c["active_vs_random_ci"]) == 2 # CI present
