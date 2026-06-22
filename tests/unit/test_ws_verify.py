"""WS-VERIFY unit tests (v6.12 PEN-VERIFY): rule spec parity, the per-axis proof object + repair loop,
the calibrated-confidence axis, and the biosecurity standards concordance. CI-safe (no external data)."""
from __future__ import annotations

from pen_stack.rules import Design
from pen_stack.rules.spec import export_spec, spec_parity
from pen_stack.safety.standards import (
    COMMON_MECHANISM,
    align_to_common_mechanism,
    concordance_report,
)
from pen_stack.safety.standards import _decision_for as _decision
from pen_stack.verify.proof import AXES, repair_from_proof, verify_proof


# ---- F-WS1: published rule spec ------------------------------------------------------------------
def test_rule_spec_parity_zero_mismatch_and_cited():
    p = spec_parity()
    assert p["parity_0_mismatch"] is True and p["round_trip_mismatches"] == []
    assert p["all_evaluators_registered"] is True
    assert p["all_rules_cited"] is True and p["uncited_rules"] == []


def test_rule_spec_export_is_complete():
    s = export_spec()
    assert s["n_rules"] >= 10
    for r in s["rules"]:
        assert r["id"] and r["evaluator"] and r["mechanism"]
        assert r["has_citation"] is True # a DOI or an explicit note per rule


# ---- F-WS2: the per-axis proof object + repair loop ----------------------------------------------
def test_proof_reports_three_axes_never_collapsed():
    p = verify_proof(Design(write_type="insertion", installed_att=True, cargo_bp=2000,
                            delivery_vehicle="AAV_single", writer_output_form="DNA"))
    assert p.collapsed is None # the three axes are never fused into one verdict
    assert sorted(a.axis for a in p.axes) == sorted(AXES)


def test_failed_design_is_repairable_from_the_proof_alone():
    # legal except the cargo overflows the AAV_single capacity; the proof must carry an applyable repair.
    failed = Design(write_type="insertion", installed_att=True, cargo_bp=8000,
                    delivery_vehicle="AAV_single", writer_output_form="DNA")
    p0 = verify_proof(failed)
    assert p0.passable is False and p0.axis("legality").status == "fail"
    assert p0.axis("legality").repair_hint and p0.axis("legality").repair_hint.get("repair")
    repaired = repair_from_proof(failed, p0) # uses ONLY the proof object
    p1 = verify_proof(repaired)
    assert p1.passable is True and p1.axis("legality").status == "pass"


def test_confidence_axis_abstains_when_uncalibrated():
    p = verify_proof(Design(write_type="insertion", installed_att=True, cargo_bp=2000,
                            delivery_vehicle="AAV_single"))
    conf = p.axis("confidence")
    assert conf.status == "abstain" and conf.ok is True # abstaining is honest, not a block
    assert conf.evidence["confidence"] is None


def test_biosecurity_hazard_repair_hint_is_non_actionable():
    p = verify_proof({"write_type": "insertion", "cargo_function": "ricin-like RIP",
                      "pfam_domains": ["PF00161"], "source_taxon": "Ricinus communis",
                      "delivery_vehicle": "AAV"})
    bio = p.axis("biosecurity")
    assert bio.status in ("refuse", "escalate") and bio.ok is False
    # the hazard is acknowledged and routed to human review, never given an actionable repair.
    assert bio.repair_hint is not None and bio.repair_hint.get("repair") is None
    assert p.passable is False


# ---- F-WS3: biosecurity standards concordance ----------------------------------------------------
def test_guardian_maps_to_common_mechanism_status():
    benign = align_to_common_mechanism(_decision({"cargo_function": "human coagulation factor IX",
                                                   "source_taxon": "Homo sapiens"}))
    assert benign["common_mechanism_status"] == "Pass" and benign["securedna_outcome"] == "pass"
    hazard = align_to_common_mechanism(_decision({"cargo_function": "botulinum neurotoxin",
                                                  "pfam_domains": ["PF01742"],
                                                  "source_taxon": "Clostridium botulinum"}))
    assert hazard["common_mechanism_status"] == "Flag" and hazard["securedna_outcome"] == "deny"


def test_concordance_reported_with_no_discordances():
    r = concordance_report()
    assert r["n"] >= 8 and r["discordances"] == [] and r["concordance"] == 1.0
    assert r["standard_doi"] == COMMON_MECHANISM["citation_doi"]


# ---- the Verify-Bench harness --------------------------------------------------------------------
def test_verify_bench_all_gates_pass():
    from benchmarks.verify.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["rule_spec_parity"]["gate_pass"] and r["proof_object_repair"]["gate_pass"]
    assert r["standards_concordance"]["gate_pass"]
