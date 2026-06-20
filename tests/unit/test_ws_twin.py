"""WS-VCELL / WS-MECH / WS-OUTCOME / WS-CAL unit tests (Phase 5.9, the digital twin).

CI-safe (closed-form mechanism + deferred/cache-replayed VC oracle + synthetic calibration). Asserts:
  * mechanistic output is computable physics, NOT a phenotype (assumptions + phenotype flag);
  * the VC oracle is OOD-gated (in-distribution -> in_scope; OOD -> extrapolating), deferred value never fabricated;
  * the fused outcome carries an interval that WIDENS under OOD, an immune-outcome from the v5.6 profile, and an
    explicit phenotype/in-vivo-magnitude boundary; in-vivo durability is conditioned on the GROUNDED NAb axis;
  * calibration is honest + two-sided (a tracking twin beats naive with CI excluding 0; a flat twin does not).
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


# --- WS-MECH ---------------------------------------------------------------------------

def test_mechanistic_is_closed_form_not_phenotype():
    m = cassette_expression({"promoter": "ef1a", "copy_number": 2}, {"accessibility": 0.5})
    assert m["relative_expression"] == pytest.approx(1.0 * 2 * 0.5) # promoter x cn x accessibility
    assert "phenotype_not_modeled" in m["scope_flags"]
    assert "steady-state" in m["assumptions"]


# --- WS-VCELL --------------------------------------------------------------------------

def test_vcell_oracle_ood_gated_and_never_fabricates():
    from pen_stack.oracles.vcell import predict_response
    ind = predict_response("k562", {"kind": "genetic"})
    ood = predict_response("rare_neuron_subtype_xyz", {"kind": "genetic"})
    assert ind.in_scope is True and ind.extrapolating is False
    assert ood.in_scope is False and ood.extrapolating is True
    assert ind.output_kind == "candidate" # a prediction is a candidate
    assert ind.value is None and ind.available is False # deferred backend -> no fabricated value


# --- WS-OUTCOME ------------------------------------------------------------------------

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


# --- WS-CAL ----------------------------------------------------------------------------

def test_calibration_is_honest_two_sided():
    rng = np.random.default_rng(0)
    obs = rng.uniform(0, 1, 40)
    tracking = obs + rng.normal(0, 0.05, 40)
    flat = np.full(40, 0.5)
    good = calibrate_outcome(tracking, obs)
    bad = calibrate_outcome(flat, obs)
    assert good["beats_naive_baseline"] is True and good["gap_ci"][0] > 0
    assert bad["beats_naive_baseline"] is False # honest negative, not hidden
    assert calibrate_outcome([0.5, 0.5], [0.4, 0.6])["available"] is False # too few -> honest abstain
