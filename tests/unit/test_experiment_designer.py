"""Experiment-designer unit tests: acquisition, batch design, retrospective validation.

CI-safe (the calibrated twin + a small synthetic retrospective). Asserts:
  * acquisition is computed from the twin's uncertainty (EIG >= 0; monotone: more uncertainty -> more EIG),
    deterministic given inputs, and immune-VOI rewards experiments that would validate a PROXY axis;
  * batch selection is diverse (beats a pure top-k-by-score selection) and carries expected info gain;
  * retrospective validation reports the active-vs-random curve-area gap with reps + a bootstrap CI, and the
    falsifiability outcome (active beats random, or a not-yet-useful) is reported either way.
"""
from __future__ import annotations

import pytest

from pen_stack.active.acquire import (
    acquisition_components,
    acquisition_score,
    coverage_novelty,
    expected_information_gain,
    feasibility_factor,
    immune_voi,
)
from pen_stack.active.design import batch_diversity, select_batch
from pen_stack.active.validate import retrospective_active_learning

_BASE = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
         "promoter": "ef1a", "copy_number": 1, "accessibility": 0.8}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- Acquisition ----------------------------------------------------------------------------

def test_eig_nonneg_and_monotone_in_uncertainty():
    ind = expected_information_gain({**_BASE, "cell_state": "k562"}, "k562")
    ood = expected_information_gain({**_BASE, "cell_state": "rare_xyz"}, "rare_xyz") # wider interval -> more EIG
    assert ind >= 0.0 and ood >= 0.0
    assert ood > ind # OOD = more reducible uncertainty


def test_eig_varies_with_cell_type_coverage():
    # regression (tester: EIG was a constant ~0.02 across every cell type). The reducible uncertainty must be
    # HIGHER in an unmeasured cell type (no atlas data there) than in a fully-measured one, EIG is no longer blind
    # to coverage. (gene/vehicle/cargo still do NOT move it: the mechanistic twin has no per-gene uncertainty, so a
    # constant there is by design, coverage is the real signal.)
    full = expected_information_gain({**_BASE, "cell_type": "k562"}, "")     # measured atlas
    partial = expected_information_gain({**_BASE, "cell_type": "hspc"}, "")  # partial atlas
    unmeasured = expected_information_gain({**_BASE, "cell_type": "ipsc"}, "")  # no atlas
    assert unmeasured > partial > full
    # same cell -> different gene/vehicle/cargo leave EIG unchanged (no per-gene mechanistic uncertainty)
    a = expected_information_gain({"gene": "AAVS1", "delivery_vehicle": "AAV_single", "cargo_bp": 3000, "cell_type": "k562"}, "")
    b = expected_information_gain({"gene": "CCR5", "delivery_vehicle": "lentivirus", "cargo_bp": 8000, "cell_type": "k562"}, "")
    assert a == b


def test_acquisition_deterministic_and_traceable():
    a = acquisition_score({**_BASE, "cell_state": "k562"}, "k562")
    b = acquisition_score({**_BASE, "cell_state": "k562"}, "k562")
    assert a == b # deterministic (no fabricated randomness)


def test_immune_voi_rewards_proxy_validating_experiments():
    # AAV immune axes are still proxies -> measuring them is high VOI
    assert immune_voi(_BASE, "k562") > 0
    # an experiment that measures only one named proxy axis scores that axis
    one = immune_voi({**_BASE, "measures_immune_axes": ["genotoxicity"]}, "k562")
    assert one == pytest.approx(1.0)


# --- Design-specific informativeness (fixes near-constant EIG) ----------

def test_immune_voi_is_in_scope_only_and_varies_by_vehicle():
    # anti-PEG is in scope for a PEGylated LNP but abstains for a non-PEG viral vehicle, so an LNP experiment
    # can validate one MORE proxy axis than AAV -> higher VOI. This is a real, design-varying signal.
    aav = immune_voi({**_BASE, "delivery_vehicle": "AAV_single", "in_vivo": True}, "k562")
    lnp = immune_voi({**_BASE, "delivery_vehicle": "lnp_mrna", "in_vivo": True}, "k562")
    assert lnp > aav


def test_coverage_novelty_higher_for_unmeasured_cell_types():
    # an unmeasured cell type has no writability atlas -> more to learn -> higher novelty than a measured one.
    assert coverage_novelty("k562") == 0.0          # full measured atlas
    assert coverage_novelty("hspc") == 0.5          # partial
    assert coverage_novelty("ipsc") == 1.0          # no atlas
    ind = acquisition_components({**_BASE, "cell_type": "k562"}, "")["acquisition"]
    ood = acquisition_components({**_BASE, "cell_type": "ipsc"}, "")["acquisition"]
    assert ood > ind  # the unmeasured-cell experiment is ranked more informative


def test_feasibility_gate_downweights_unbuildable_experiments():
    feasible = acquisition_components({**_BASE, "delivery_vehicle": "lentivirus", "cargo_bp": 6000}, "k562")
    infeasible = acquisition_components({**_BASE, "delivery_vehicle": "AAV_single", "cargo_bp": 6000}, "k562")  # >4.7kb cap
    assert feasibility_factor({"delivery_vehicle": "AAV_single", "cargo_bp": 6000}) < 1.0
    assert infeasible["buildable"] is False and feasible["buildable"] is True
    assert infeasible["acquisition"] < feasible["acquisition"]  # can't-build -> less informative


def test_batch_marginal_gain_is_distinct_and_decreasing():
    # the marginal gain (submodular greedy objective at selection) decreases down the batch and is not a constant,
    # even when several experiments share the same intrinsic acquisition (the tester's "same value everywhere").
    cands = [{**_BASE, "delivery_vehicle": v, "cell_type": c}
             for v in ("AAV_single", "lentivirus", "lnp_mrna", "electroporation")
             for c in ("ipsc", "cd8_t", "pbmc")]
    batch = select_batch(cands, "", k=6)
    mgs = [b["marginal_gain"] for b in batch]
    assert all("marginal_gain" in b and "acquisition" in b and "rank" in b for b in batch)
    assert all(mgs[i] >= mgs[i + 1] for i in range(len(mgs) - 1))  # diminishing returns
    assert len(set(mgs)) > 1  # NOT a single constant value


# --- Batch design -------------------------------------------------------------------------

def test_batch_is_diverse_and_carries_eig():
    cands = [{**_BASE, "delivery_vehicle": v, "cell_state": "k562"}
             for v in ("AAV_single", "AAV_dual", "lentivirus", "helper_dependent_adenovirus")]
    diverse = select_batch(cands, "k562", k=3, w_div=0.8)
    greedy = select_batch(cands, "k562", k=3, w_div=0.0) # pure top-k-by-score
    assert all("expected_info_gain" in b for b in diverse)
    assert batch_diversity(diverse) >= batch_diversity(greedy) # diversity term helps spread the batch
    assert len({b["delivery_vehicle"] for b in diverse}) >= 2


# --- Retrospective validation -----------------------------------------------------------------------

def test_retrospective_reports_gap_and_ci():
    r = retrospective_active_learning(reps=12, rounds=6)
    assert r["no_fabrication"] is True
    gap = r["active_vs_random"]
    assert "ci" in gap and "mean_gap" in gap
    assert isinstance(r["active_beats_random"], bool) # reported either way (falsifiable)
    for s in ("active", "random", "greedy"): # learning curves present per strategy
        assert "mean" in r["curves"][s]
