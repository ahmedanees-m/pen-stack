"""Rule-spec parity, the per-axis proof object + repair loop,
the calibrated-confidence axis, and the biosecurity standards concordance. CI-safe (no external data)."""
from __future__ import annotations

import pytest

from pen_stack.rules import Design
from pen_stack.rules.spec import export_spec, spec_parity
from pen_stack.safety.standards import (
    align_to_common_mechanism,
    concordance_report,
)
from pen_stack.safety.standards import _decision_for as _decision
from pen_stack.verify.proof import AXES, repair_from_proof, verify_proof


# ---- published rule spec ------------------------------------------------------------------
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


# ---- the per-axis proof object + repair loop ----------------------------------------------
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
    assert conf.status == "abstain" and conf.ok is True # abstaining is not a block
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


def test_biosecurity_axis_carries_reason_and_citation_not_just_a_bare_signature_id():
    """Design Studio's Proof previously reduced a hazard hit to {signature, kind, severity} with no
    reason or citation, unlike Guardian's own /api/safety view of the same hit. The Proof's violated list
    must carry the same detail so both surfaces are equally informative."""
    p = verify_proof({"write_type": "insertion", "cargo_function": "ricin-like RIP",
                      "pfam_domains": ["PF00161"], "delivery_vehicle": "AAV"})
    bio = p.axis("biosecurity")
    assert bio.violated and bio.violated[0]["reason"]
    assert bio.violated[0]["citation"]


def test_legality_and_confidence_are_not_evaluated_when_biosecurity_refuses():
    # Tester-found (App_testing_debugging.txt): verify.service short-circuits on a
    # biosecurity refuse and returns BEFORE the rules engine or confidence calibration ever run, legality and
    # confidence were never evaluated. Reporting them as "fail"/"abstain" (the old behavior) fabricates a
    # verdict for an axis that never ran, and for confidence ships an ACTIVELY WRONG repair hint ("supply the
    # soft scores") since supplying them would not help, the block happens before they would be read. Both
    # axes must report not_evaluated, must not themselves block (biosecurity alone accounts for the
    # block, mirrors the existing "abstaining is not a block" convention), and must carry no misleading
    # or actionable repair.
    p = verify_proof({"write_type": "insertion", "cargo_function": "ricin-like RIP",
                      "pfam_domains": ["PF00161"], "source_taxon": "Ricinus communis",
                      "delivery_vehicle": "AAV"})
    leg, conf, bio = p.axis("legality"), p.axis("confidence"), p.axis("biosecurity")
    assert leg.status == "not_evaluated" and leg.ok is True and leg.violated == []
    assert conf.status == "not_evaluated" and conf.ok is True
    assert leg.repair_hint and leg.repair_hint.get("repair") is None
    assert conf.repair_hint and conf.repair_hint.get("repair") is None
    assert "supply the soft" not in (conf.repair_hint.get("text") or "").lower()  # the misleading hint is gone
    assert bio.ok is False and p.passable is False  # biosecurity alone correctly still blocks


def test_legality_still_fails_normally_when_biosecurity_does_not_refuse():
    # guard against a regression where the not_evaluated branch swallows genuine legality failures: a plain
    # capacity violation (no biosecurity hazard) must still report a real "fail" with rule/citation/repair.
    failed = Design(write_type="insertion", installed_att=True, cargo_bp=8000,
                    delivery_vehicle="AAV_single", writer_output_form="DNA")
    p = verify_proof(failed)
    leg = p.axis("legality")
    assert leg.status == "fail" and leg.violated and leg.repair_hint.get("repair")


# ---- biosecurity standards concordance ----------------------------------------------------
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


def test_standards_concordance_reachable_via_rest_api():
    # Tester-found: concordance_report() + align_to_common_mechanism() existed but had NO API/UI surface
    # ("Standards concordance not located" on the Guardian page). GET /safety/concordance now serves the labelled
    # probe-set report; POST /safety carries a per-decision `standards` alignment (additive, decision unchanged).
    pytest.importorskip("fastapi")  # server extra (fastapi + httpx); skips on a core-only install / CI
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from pen_stack.server.api import app
    c = TestClient(app)
    conc = c.get("/safety/concordance").json()
    assert conc["n"] >= 8 and conc["discordances"] == []
    sv = c.post("/safety", json={"cargo_function": "human factor IX", "pfam_domains": []}).json()
    assert sv["decision"] == "clear"  # the decision itself is unchanged by the additive field
    assert sv["standards"]["common_mechanism_status"] == "Pass" and sv["standards"]["securedna_outcome"] == "pass"


# ---- the Verify-Bench harness --------------------------------------------------------------------
def test_verify_bench_all_gates_pass():
    from benchmarks.verify.harness import run
    r = run()
    assert r["all_gates_pass"] is True
    assert r["rule_spec_parity"]["gate_pass"] and r["proof_object_repair"]["gate_pass"]
    assert r["standards_concordance"]["gate_pass"]
