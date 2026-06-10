"""WS-GENOTOX unit tests (Phase 5.2) - the COMPUTED genotoxicity oracle (integration-site x COSMIC-oncogene).

CI-safe: runs entirely off the COMMITTED summary artifact configs/genotoxicity_oracle.yaml (the raw VISDB
catalogues stay on the VM; only the auditable per-class statistics ship). Asserts: integrating vectors get a
data-derived score via the v4.0 OracleResult contract; non-integrating vectors are 1.0 by mechanism; the
oracle abstains (never fabricates) when it has no computed class; the computation reproduces the
lentivirus-safer-than-gammaretrovirus ordering FROM DATA and validates the v5.1 documented tier; the in-vivo
clonal OUTCOME stays a known-unknown."""
from __future__ import annotations

import yaml

from pen_stack._resources import resource
from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.delivery_immunology import safety_efficacy_profile
from pen_stack.planner.genotoxicity_oracle import (
    computed_genotox_score,
    genotoxicity_oracle,
)


def _artifact():
    return yaml.safe_load(resource("configs/genotoxicity_oracle.yaml").read_text(encoding="utf-8"))


def test_integrating_vector_gets_computed_oracle_result():
    r = genotoxicity_oracle("lentivirus")
    assert r.available is True and r.output_kind == "baseline"   # observed-data comparator, not a candidate
    assert r.oracle == "genome" and r.scope_card == "delivery_genotoxicity"
    v = r.value
    assert v["vector_class"] == "lentiviral"
    assert v["enrichment"] > 1.0                                 # integration enriched near oncogenes vs bg
    assert 0.0 < v["genotox_score"] <= 1.0
    assert abs(v["genotox_score"] - 1.0 / v["enrichment"]) < 2e-3   # score = 1/enrichment (3-dp rounded)
    assert r.native_uncertainty is not None and r.extrapolating is False  # HIV n is large -> robust


def test_non_integrating_vector_is_safe_by_mechanism():
    for veh in ("AAV_single", "lnp_mrna", "helper_dependent_adenovirus", "electroporation"):
        r = genotoxicity_oracle(veh)
        assert r.available is True
        assert r.value["genotox_score"] == 1.0 and r.value["mechanism"] == "non-integrating"
        assert r.extrapolating is False


def test_oracle_abstains_rather_than_fabricates():
    # unknown vehicle -> not available, no value (caller falls back to the documented tier)
    r = genotoxicity_oracle("not_a_vehicle")
    assert r.available is False and r.value is None
    score, res = computed_genotox_score("not_a_vehicle")
    assert score is None and res.available is False


def test_reproduces_lentivirus_safer_than_gammaretrovirus_from_data():
    cls = _artifact()["classes"]
    # the data ordering: lentiviral integration is LESS oncogene-proximal than gammaretroviral (the LMO2 / SCID-X1
    # pattern) -> lentiviral enrichment < gammaretroviral enrichment. This is the documented fact, from data.
    assert cls["lentiviral"]["enrichment"] < cls["gammaretroviral"]["enrichment"]
    assert cls["lentiviral"]["robust"] is True                  # the in-palette class is well-powered
    # the small-n comparator is honestly flagged (directional only)
    assert cls["gammaretroviral"]["robust"] is False


def test_computed_score_validates_the_documented_tier():
    # v5.1 documented lentivirus genotoxicity = "moderate" -> tier score 0.5; the v5.2 COMPUTED score should
    # land close to it (the prior is confirmed by data, not contradicted).
    p = safety_efficacy_profile("lentivirus")
    assert p["genotox_source"] == "computed"
    assert abs(p["genotox_score"] - 0.5) < 0.1
    assert p["genotox_provenance"] and "COSMIC" in p["genotox_provenance"]


def test_provenance_dois_are_curated_and_magnitude_stays_known_unknown():
    art = _artifact()
    assert citations_grounded(art["provenance_dois"])["all_grounded"] is True
    # the oracle's note disclaims the in-vivo clonal OUTCOME (it is a known-unknown, not modelled)
    r = genotoxicity_oracle("lentivirus")
    assert "known-unknown" in r.note.lower()
    # scope card explicitly excludes the in-vivo leukemogenesis outcome
    cards = yaml.safe_load(resource("configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    assert "leukemogenesis" in cards["delivery_genotoxicity"]["not_valid_for"].lower()
