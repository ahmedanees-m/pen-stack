"""WS-PEG unit tests (Phase 5.6) - anti-PEG immunity oracle (gates LNP re-dosing).

CI-safe (curated serosurvey table + arithmetic). Asserts: PEGylated LNP -> a score with the prevalence range
surfaced as native uncertainty; non-PEGylated vehicles abstain; re-dosing relevance noted; patient titer stays
a known-unknown; serosurvey DOIs curated."""
from __future__ import annotations

import yaml

from pen_stack._resources import resource
from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.antipeg_oracle import _all_dois, antipeg_oracle, computed_antipeg_score


def test_pegylated_lnp_gets_score_with_range():
    r = antipeg_oracle("lnp_mrna")
    assert r.available is True and r.output_kind == "baseline" and r.scope_card == "antipeg"
    lo, hi = r.value["anti_peg_prevalence_pct"]
    assert abs(r.value["preexisting_antipeg_score"] - (1.0 - (lo + hi) / 2.0 / 100.0)) < 1e-6
    assert r.native_uncertainty == round((hi - lo) / 200.0, 4) # range half-width surfaced
    assert r.value["gates"] == "re-dosing" and "re-dosing" in r.note.lower()


def test_non_pegylated_vehicle_abstains():
    for veh in ("AAV_single", "lentivirus", "helper_dependent_adenovirus", "evlp", "electroporation"):
        r = antipeg_oracle(veh)
        assert r.available is False and r.value is None
    score, res = computed_antipeg_score("AAV_single")
    assert score is None and res.available is False


def test_pegylated_override_forces_computation():
    r = antipeg_oracle("evlp", pegylated=True)
    assert r.available is True and r.value["preexisting_antipeg_score"] is not None


def test_provenance_curated_and_patient_titer_is_known_unknown():
    assert len(_all_dois()) >= 1
    assert citations_grounded(_all_dois())["all_grounded"] is True
    r = antipeg_oracle("lnp_mrna")
    assert "known-unknown" in r.note.lower() and "titer" in r.note.lower()
    cards = yaml.safe_load(resource("configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    nv = cards["antipeg"]["not_valid_for"].lower()
    assert "patient" in nv and "induced" in nv
