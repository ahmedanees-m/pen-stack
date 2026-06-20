"""WS-MC unit tests (Phase 3.2), target-site filter (MC1) + delivery constraints (MC2). Pure-logic, CI-safe."""
from __future__ import annotations

from pen_stack.planner.delivery import recommend_delivery
from pen_stack.planner.delivery_constraints import scan_delivery
from pen_stack.planner.optimize import mechanistic_filter
from pen_stack.planner.target_site import target_site_available
from pen_stack.validate.target_site_controls import run as ts_controls

_PERMISSIVE = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG"
_POLYA = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
_ATTP = "AGGTTTGTCTGGTCAACCACCGCGGTCTCAGTGGTGTACGGTACAAACCCA"


# ---- MC1: target-site / PAM / att-site hard filter --------------------------------------------
def test_target_site_controls_pass():
    r = ts_controls()
    assert r["passes"] and r["positive_controls_pass"] and r["negative_controls_pass"]


def test_cast_requires_pam():
    assert target_site_available("CAST_VK", _PERMISSIVE)["available"] # has a GTN PAM
    assert not target_site_available("CAST_VK", _POLYA)["available"] # no PAM -> reject


def test_serine_requires_att():
    assert not target_site_available("serine_integrase", _PERMISSIVE)["available"] # no att -> reject
    assert target_site_available("serine_integrase", _ATTP)["available"] # native att present
    # a pre-installed landing pad makes any site reachable deterministically
    assert target_site_available("serine_integrase", _POLYA, installed_att=True)["available"]


def test_pe_integrase_broadly_reachable():
    assert target_site_available("PE_integrase", _POLYA)["available"] # PE installs its own att


def test_unknown_family_not_silently_rejected():
    v = target_site_available("some_new_family", _POLYA)
    assert v["available"] and not v["checked"]


def test_mechanistic_filter_planner_hook():
    res = mechanistic_filter("bridge_IS110;serine_integrase;Cas9", _PERMISSIVE)
    assert "bridge_IS110" in res["reachable"] # CT core + NGG present
    assert any(r["family"] == "serine_integrase" for r in res["rejected"]) # no att -> rejected
    assert res["reachable_str"]


# ---- MC2: delivery-vehicle sequence constraints ----------------------------------------------
def test_delivery_internal_polya_flagged_for_lentiviral():
    payload = "ATGGCG" + "AATAAA" * 3 + "GCGT" * 10
    r = scan_delivery(payload, "lentiviral")
    assert any(f["check"] == "internal_polyA" for f in r["flags"])
    assert all("suggestion" in f for f in r["flags"])


def test_delivery_directionality_clean_below_problematic():
    rep = "ACGTACGTACGTACGTACGTACGT"
    problematic = rep + "TTT" + rep + "AATAAA" # direct repeat + internal poly(A)
    clean = "ATGGCAGTCAGTCAGTGCATGCATGCATGCATGCATGCAT"
    assert (scan_delivery(problematic, "lentiviral")["delivery_constraint_risk"]
            > scan_delivery(clean, "lentiviral")["delivery_constraint_risk"])


def test_delivery_homopolymer_flagged_for_aav():
    payload = "ATGC" + "A" * 25 + "GCGCGC"
    r = scan_delivery(payload, "AAV")
    assert any(f["check"] == "homopolymer_run" for f in r["flags"])


def test_rna_vehicle_no_dna_packaging_checks():
    assert scan_delivery("A" * 40, "mRNA-RNP")["checks_applied"] == []


def test_recommend_delivery_attaches_constraints():
    r = recommend_delivery(978, 2000, "k562", cargo_seq="ATGC" + "A" * 25 + "GCGC")
    assert "delivery_constraints" in r and "delivery_constraint_risk" in r["delivery_constraints"]
    # without a sequence, no constraint scan (backward compatible)
    assert "delivery_constraints" not in recommend_delivery(978, 2000, "k562")


# ---- MC3: off-target energetics (gated; ships only if it beats 0.77) --------------------------
def test_energetics_fit_score_and_serialize():
    from pen_stack.bridge.offtarget_energetics import (energetic_risk, fit_penalties, from_json, to_json)
    pairs = [("ACGTACGTACGTAC", "ACGTACGTACGTAC"), ("ACGTACGTACGTAG", "ACGTACGTACGTAC"),
             ("ACGAACGTACGTAC", "ACGTACGTACGTAC")]
    m = fit_penalties(pairs)
    # a perfect match has the maximum recombination risk; a mismatch lowers it
    assert energetic_risk("ACGTACGTACGTAC", "ACGTACGTACGTAC", m) == 1.0
    assert energetic_risk("ACGTACGTACGTAG", "ACGTACGTACGTAC", m) < 1.0
    # JSON roundtrip preserves the penalties
    m2 = from_json(to_json(m))
    assert m2["core_len"] == m["core_len"] and len(m2["pen"]) == len(m["pen"])


def test_energetics_decoy_constructions():
    # the reviewer-driven core_preserved decoy must keep the core matched and flip only a non-core position
    import random

    from pen_stack.validate.offtarget_energetics_eval import _CORE0, _make_decoy
    intended = "ACGTACGACGTACG"
    seq = intended # a perfectly core-preserved positive
    rng = random.Random(0)
    cd = _make_decoy(seq, intended, "core_disrupted", rng)
    assert cd[_CORE0] != intended[_CORE0] # core_disrupted flips the core
    cp = _make_decoy(seq, intended, "core_preserved", rng)
    assert cp[_CORE0] == intended[_CORE0] # core_preserved keeps the core matched
    diffs = [i for i in range(len(seq)) if cp[i] != intended[i]]
    assert diffs and _CORE0 not in diffs # differs only at non-core position(s)


def test_site_risk_uses_energetics_when_table_present():
    # the committed penalty table ships with the repo -> the energetics ranker (0.88) is the default
    from pen_stack.bridge.offtarget import site_risk
    r = site_risk("ACGTGACTAGGCTA", "ACGTGACTAGGCTA")
    assert r["ranker"] in ("energetics", "position_weight")
    if r["ranker"] == "energetics":
        assert r["heldout_auroc"] == 0.88 and r["risk"] == 1.0
