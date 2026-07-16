"""Digital-twin unit tests: mechanistic model, VC oracle, fused outcome, calibration.

CI-safe (closed-form mechanism + deferred/cache-replayed VC oracle + synthetic calibration). Asserts:
  * mechanistic output is computable physics, NOT a phenotype (assumptions + phenotype flag);
  * the VC oracle is OOD-gated (in-distribution -> in_scope; OOD -> extrapolating), deferred value never fabricated;
  * the fused outcome carries an interval that WIDENS under OOD, an immune-outcome from the v5.6 profile, and an
    explicit phenotype/in-vivo-magnitude boundary; in-vivo durability is conditioned on the GROUNDED NAb axis;
  * calibration is two-sided (a tracking twin beats naive with CI excluding 0; a flat twin does not).
"""
from __future__ import annotations

import numpy as np
import pytest

from pen_stack.twin.calibrate import calibrate_outcome
from pen_stack.twin.mechanistic import cassette_expression
from pen_stack.twin.outcome import predict_outcome

_DESIGN = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19", "delivery_vehicle": "AAV_single",
           "promoter": "ef1a", "copy_number": 1, "accessibility": 0.8, "writer_output_form": "dsDNA"}


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


# --- mechanistic ---------------------------------------------------------------------------

def test_mechanistic_is_closed_form_not_phenotype():
    m = cassette_expression({"promoter": "ef1a", "copy_number": 2}, {"accessibility": 0.5})
    assert m["relative_expression"] == pytest.approx(1.0 * 2 * 0.5) # promoter x cn x accessibility
    assert "phenotype_not_modeled" in m["scope_flags"]
    assert "steady-state" in m["assumptions"]


# --- VC oracle --------------------------------------------------------------------------

def test_vcell_oracle_ood_gated_and_never_fabricates():
    from pen_stack.oracles.vcell import predict_response
    ind = predict_response("k562", {"kind": "genetic"})
    ood = predict_response("rare_neuron_subtype_xyz", {"kind": "genetic"})
    assert ind.in_scope is True and ind.extrapolating is False
    assert ood.in_scope is False and ood.extrapolating is True
    assert ind.output_kind == "candidate" # a prediction is a candidate
    assert ind.value is None and ind.available is False # deferred backend -> no fabricated value


# --- outcome ------------------------------------------------------------------------

def test_outcome_carries_interval_immune_and_phenotype_boundary():
    o = predict_outcome(_DESIGN, "k562")
    assert o["output_kind"] == "candidate" and o["no_fabrication"] is True
    lo, hi = o["interval"]
    assert lo <= o["predicted_outcome"]["relative_expression"] <= hi
    assert o["immune_outcome"] is not None and "axes" in o["immune_outcome"]
    assert "phenotype_not_modeled" in o["scope_flags"] and "in_vivo_magnitude_unknown" in o["scope_flags"]


def test_ood_widens_the_interval():
    ind = predict_outcome(_DESIGN, "k562")
    ood = predict_outcome(_DESIGN, "rare_neuron_subtype_xyz")
    assert ood["extrapolating"] is True and "vcell_OOD" in ood["scope_flags"]
    assert (ood["interval"][1] - ood["interval"][0]) > (ind["interval"][1] - ind["interval"][0])


def test_in_vivo_durability_conditioned_on_grounded_nab():
    o = predict_outcome(_DESIGN, "k562") # AAV_single is in-vivo
    assert o["conditioned_on_preexisting_nab"] is not None
    # ex-vivo vehicle -> no NAb conditioning
    ex = predict_outcome({**_DESIGN, "delivery_vehicle": "lentivirus"}, "k562")
    assert ex["conditioned_on_preexisting_nab"] is None


def test_cargo_over_capacity_flags_infeasible(): # tester finding
    # relative expression is per-copy (cargo-size-INDEPENDENT), so cargo size must not move the number, but a
    # cargo that overflows the vehicle can't be built, and that must be surfaced (not silently "buildable").
    small = predict_outcome({**_DESIGN, "cargo_bp": 3000}, "k562")
    big = predict_outcome({**_DESIGN, "cargo_bp": 50000}, "k562")  # 50 kb >> AAV_single 4.7 kb
    assert small["feasibility"]["buildable"] is True
    assert big["feasibility"]["buildable"] is False and "cargo_exceeds_vehicle_capacity" in big["scope_flags"]
    # per-copy: cargo size alone does NOT change the mechanistic relative expression
    assert small["predicted_outcome"]["relative_expression"] == big["predicted_outcome"]["relative_expression"]


def test_nonpositive_cargo_is_not_buildable(): # tester finding (cargo_bp=0 read as buildable)
    for bad in (0, -100):
        o = predict_outcome({**_DESIGN, "cargo_bp": bad}, "k562")
        assert o["feasibility"]["buildable"] is False, bad
        assert "cargo_size_nonpositive" in o["scope_flags"]


def test_promoter_is_a_live_lever_on_the_mechanistic_estimate(): # tester finding (palette not selectable)
    from pen_stack.twin.mechanistic import promoter_palette
    pal = promoter_palette()
    assert len(pal) >= 25 and all(p["name"] and p["strength"] is not None for p in pal)
    strong = predict_outcome({**_DESIGN, "promoter": "ef1a"}, "k562")["predicted_outcome"]["relative_expression"]
    weak = predict_outcome({**_DESIGN, "promoter": "desmin"}, "k562")["predicted_outcome"]["relative_expression"]
    assert strong != weak  # the mechanistic estimate genuinely reacts to the chosen promoter


# --- calibration ----------------------------------------------------------------------------

def test_calibration_is_two_sided():
    rng = np.random.default_rng(0)
    obs = rng.uniform(0, 1, 40)
    tracking = obs + rng.normal(0, 0.05, 40)
    flat = np.full(40, 0.5)
    good = calibrate_outcome(tracking, obs)
    bad = calibrate_outcome(flat, obs)
    assert good["beats_naive_baseline"] is True and good["gap_ci"][0] > 0
    assert bad["beats_naive_baseline"] is False # negative, not hidden
    assert calibrate_outcome([0.5, 0.5], [0.4, 0.6])["available"] is False # too few -> abstain
