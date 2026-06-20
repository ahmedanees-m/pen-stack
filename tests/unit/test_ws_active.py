"""WS-ACQ / WS-DESIGN / WS-VALIDATE unit tests (Phase 5.10, the experiment designer).

CI-safe (the calibrated v5.9 twin + a small synthetic retrospective). Asserts:
  * acquisition is computed from the twin's uncertainty (EIG >= 0; monotone: more uncertainty -> more EIG),
    deterministic given inputs, and immune-VOI rewards experiments that would validate a PROXY axis;
  * batch selection is diverse (beats a pure top-k-by-score selection) and carries expected info gain;
  * retrospective validation reports the active-vs-random curve-area gap with reps + a bootstrap CI, and the
    falsifiability outcome (active beats random, or an honest not-yet-useful) is reported either way.
"""
from __future__ import annotations

import pytest

from pen_stack.active.acquire import (
    acquisition_score,
    expected_information_gain,
    immune_voi,
)
from pen_stack.active.design import batch_diversity, select_batch
from pen_stack.active.validate import retrospective_active_learning

_BASE = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
         "promoter": "ef1a", "copy_number": 1, "accessibility": 0.8}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- WS-ACQ ----------------------------------------------------------------------------

def test_eig_nonneg_and_monotone_in_uncertainty():
    ind = expected_information_gain({**_BASE, "cell_state": "k562"}, "k562")
    ood = expected_information_gain({**_BASE, "cell_state": "rare_xyz"}, "rare_xyz") # wider interval -> more EIG
    assert ind >= 0.0 and ood >= 0.0
    assert ood > ind # OOD = more reducible uncertainty


def test_acquisition_deterministic_and_traceable():
    a = acquisition_score({**_BASE, "cell_state": "k562"}, "k562")
    b = acquisition_score({**_BASE, "cell_state": "k562"}, "k562")
    assert a == b # deterministic (no fabricated randomness)


def test_immune_voi_rewards_proxy_validating_experiments():
    # AAV immune axes are still proxies (v5.6) -> measuring them is high VOI
    assert immune_voi(_BASE, "k562") > 0
    # an experiment that measures only one named proxy axis scores that axis
    one = immune_voi({**_BASE, "measures_immune_axes": ["genotoxicity"]}, "k562")
    assert one == pytest.approx(1.0)


# --- WS-DESIGN -------------------------------------------------------------------------

def test_batch_is_diverse_and_carries_eig():
    cands = [{**_BASE, "delivery_vehicle": v, "cell_state": "k562"}
             for v in ("AAV_single", "AAV_dual", "lentivirus", "helper_dependent_adenovirus")]
    diverse = select_batch(cands, "k562", k=3, w_div=0.8)
    greedy = select_batch(cands, "k562", k=3, w_div=0.0) # pure top-k-by-score
    assert all("expected_info_gain" in b for b in diverse)
    assert batch_diversity(diverse) >= batch_diversity(greedy) # diversity term helps spread the batch
    assert len({b["delivery_vehicle"] for b in diverse}) >= 2


# --- WS-VALIDATE -----------------------------------------------------------------------

def test_retrospective_reports_gap_and_ci_honestly():
    r = retrospective_active_learning(reps=12, rounds=6)
    assert r["no_fabrication"] is True
    gap = r["active_vs_random"]
    assert "ci" in gap and "mean_gap" in gap
    assert isinstance(r["active_beats_random"], bool) # reported either way (falsifiable)
    for s in ("active", "random", "greedy"): # learning curves present per strategy
        assert "mean" in r["curves"][s]
