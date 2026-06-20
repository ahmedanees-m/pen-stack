"""WS-EPITOPE unit tests (Phase 5.3) - the COMPUTED capsid/envelope CD8 T-cell epitope-load oracle (MHCflurry).

CI-safe: runs off the COMMITTED summary artifact configs/capsid_epitope_oracle.yaml (the MHCflurry run + raw
sequences stay on the VM; only the per-vehicle statistics ship). Asserts: every viral vector gets a computed
intrinsic-presentability score via the v4.0 OracleResult contract; non-viral vectors are 1.0 by mechanism; ALL
8 vehicles are covered (computed or by-mechanism); the computed signal is folded into the adaptive axis only
for IN-VIVO vehicles (ex-vivo lentivirus is reported but muted); the realized patient-HLA-specific response
stays a known-unknown."""
from __future__ import annotations

import yaml

from pen_stack._resources import resource
from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.capsid_epitope_oracle import (
    capsid_epitope_oracle,
    computed_capsid_immune_score,
)
from pen_stack.planner.delivery_immunology import safety_efficacy_profile
from pen_stack.planner.delivery_vehicles import names


def _artifact():
    return yaml.safe_load(resource("configs/capsid_epitope_oracle.yaml").read_text(encoding="utf-8"))


def test_viral_vector_gets_computed_capsid_epitope_result():
    r = capsid_epitope_oracle("AAV_single")
    assert r.available is True and r.output_kind == "baseline"
    assert r.oracle == "protein_design" and r.scope_card == "capsid_epitope"
    v = r.value
    assert 0.0 <= v["epitope_fraction_strong"] <= 1.0
    assert abs(v["capsid_immune_score"] - (1.0 - v["epitope_fraction_strong"])) < 1e-6
    assert v["antigens"] == ["AAV2_VP1"]
    # v6.9.2: PRIMARY predictor is the real NetMHCpan-4.1; MHCflurry is reported as an explicit cross-check
    assert v["predictor"] == "NetMHCpan-4.1"
    assert v["cross_check_mhcflurry"]["capsid_immune_score"] is not None
    assert "NetMHCpan-4.1" in r.note


def test_non_viral_vector_has_no_capsid_load_by_mechanism():
    for veh in ("lnp_mrna", "evlp", "electroporation"):
        r = capsid_epitope_oracle(veh)
        assert r.available is True
        assert r.value["capsid_immune_score"] == 1.0 and r.value["mechanism"] == "non-viral"


def test_all_eight_vehicles_are_covered():
    # "cover all the vectors": every known vehicle gets a computed result (viral computed OR non-viral 1.0).
    for veh in names():
        r = capsid_epitope_oracle(veh)
        assert r.available is True, veh
        assert r.value["capsid_immune_score"] is not None, veh


def test_oracle_abstains_for_unknown_vehicle():
    r = capsid_epitope_oracle("not_a_vehicle")
    assert r.available is False and r.value is None
    score, res = computed_capsid_immune_score("not_a_vehicle")
    assert score is None and res.available is False


def test_aav_is_less_epitope_dense_than_adenovirus():
    # the computed ordering: AAV2 capsid is LESS presentable than the Ad5 hexon (Ad is the more immunogenic
    # capsid) -> AAV capsid_immune_score > HDAd capsid_immune_score. Consistent with the documented tiers.
    # BOTH the primary NetMHCpan-4.1 (oracle) AND the MHCflurry cross-check (cache) agree on this ordering.
    aav = capsid_epitope_oracle("AAV_single").value["capsid_immune_score"] # NetMHCpan-4.1 primary
    hdad = capsid_epitope_oracle("helper_dependent_adenovirus").value["capsid_immune_score"]
    assert aav > hdad
    art = _artifact()["vehicles"] # MHCflurry cross-check
    assert art["AAV_single"]["capsid_immune_score"] > art["helper_dependent_adenovirus"]["capsid_immune_score"]


def test_computed_folds_only_for_in_vivo_vehicles():
    # AAV is in-vivo -> the computed capsid score IS folded into the adaptive axis.
    aav = safety_efficacy_profile("AAV_single")
    assert aav["adaptive_source"] == "computed"
    assert aav["capsid_presentability_score"] is not None
    # lentivirus is EX-VIVO: the intrinsic VSV-G presentability is reported but NOT folded (documented tier kept).
    lv = safety_efficacy_profile("lentivirus")
    assert lv["adaptive_source"] == "computed_ex_vivo_muted"
    assert lv["capsid_presentability_score"] is not None
    assert lv["immune_score"] == 1.0 # documented "low" adaptive kept (ex-vivo); not overridden


def test_provenance_curated_and_patient_response_stays_known_unknown():
    art = _artifact()
    assert citations_grounded(art["provenance_dois"])["all_grounded"] is True
    r = capsid_epitope_oracle("AAV_single")
    assert "known-unknown" in r.note.lower()
    cards = yaml.safe_load(resource("configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    nv = cards["capsid_epitope"]["not_valid_for"].lower()
    assert "patient" in nv and ("antibody" in nv or "neutralizing" in nv)
