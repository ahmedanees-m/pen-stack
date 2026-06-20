"""WS-SEROPREV unit tests (Phase 5.5) - anti-vector neutralizing-antibody seroprevalence oracle.

The pre-existing-humoral-immunity axis is the one immune axis that is EMPIRICAL, not sequence-computable: it is
grounded in published serosurvey DATA (configs/seroprevalence.yaml). CI-safe (curated table + arithmetic).
Asserts: per-serotype seroprevalence maps to a pre-existing score; the ordering matches the literature
(adenovirus > AAV > VSV pre-existing immunity); non-viral vehicles are 1.0 by mechanism; the score folds into
the preexisting axis for in-vivo vehicles and is muted for ex-vivo; the individual patient's NAb titer stays a
known-unknown."""
from __future__ import annotations

import yaml

from pen_stack._resources import resource
from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.delivery_immunology import safety_efficacy_profile
from pen_stack.planner.seroprevalence_oracle import (
    _all_dois,
    computed_preexisting_score,
    seroprevalence_oracle,
)


def test_seroprevalence_maps_to_preexisting_score():
    r = seroprevalence_oracle("AAV_single")
    assert r.available and r.output_kind == "baseline" and r.scope_card == "seroprevalence"
    lo, hi = r.value["nab_seroprevalence_pct"]
    assert abs(r.value["preexisting_score"] - (1.0 - (lo + hi) / 2.0 / 100.0)) < 1e-6
    assert r.native_uncertainty is not None # the range width is surfaced as uncertainty
    assert r.value["dois"]


def test_ordering_matches_literature():
    # adenovirus has the HIGHEST pre-existing seroprevalence, VSV (lentivirus) the lowest -> the pre-existing
    # SCORE (1 = fewest excluded) orders VSV > AAV > Ad5.
    ad = seroprevalence_oracle("helper_dependent_adenovirus").value["preexisting_score"]
    aav = seroprevalence_oracle("AAV_single").value["preexisting_score"]
    vsv = seroprevalence_oracle("lentivirus").value["preexisting_score"]
    assert vsv > aav > ad


def test_non_viral_has_no_preexisting_antivector_immunity():
    for veh in ("lnp_mrna", "evlp", "electroporation"):
        r = seroprevalence_oracle(veh)
        assert r.available and r.value["preexisting_score"] == 1.0 and r.value["mechanism"] == "non-viral"


def test_explicit_serotype_overrides_vehicle_default():
    r = seroprevalence_oracle("AAV_single", serotype="AAV8")
    assert r.value["serotype"] == "AAV8"
    # AAV8 has lower pre-existing immunity than AAV2 -> a higher pre-existing score
    assert (seroprevalence_oracle("AAV_single", serotype="AAV8").value["preexisting_score"]
            > seroprevalence_oracle("AAV_single", serotype="AAV2").value["preexisting_score"])


def test_oracle_abstains_for_unknown_vehicle():
    r = seroprevalence_oracle("not_a_vehicle")
    assert r.available is False and r.value is None
    score, res = computed_preexisting_score("not_a_vehicle")
    assert score is None and res.available is False


def test_folds_for_in_vivo_muted_for_ex_vivo():
    aav = safety_efficacy_profile("AAV_single")
    assert aav["preexisting_source"] == "computed" and aav["seroprevalence_score"] is not None
    lv = safety_efficacy_profile("lentivirus") # ex-vivo: serum NAb cannot reach ex-vivo cells
    assert lv["preexisting_source"] == "computed_ex_vivo_muted"
    assert lv["immune_score"] == 1.0 # documented "low" preexisting kept (not overridden)


def test_provenance_curated_and_patient_titer_is_known_unknown():
    assert citations_grounded(_all_dois())["all_grounded"] is True
    r = seroprevalence_oracle("AAV_single")
    assert "population" in r.note.lower() and "known-unknown" in r.note.lower()
    cards = yaml.safe_load(resource("configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    assert "patient" in cards["seroprevalence"]["not_valid_for"].lower()
