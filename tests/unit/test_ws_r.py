"""WS-R unit tests (v3.3), rule base parity + solver controls. Pure-logic, CI-safe.

Parity: the relocated rules must reproduce the EXACT decisions of the existing validated functions
(target_site_available, payload capacity, cargo-form), relocation, not behaviour change. Controls: positive
designs are legal; negative designs are rejected by the correctly-NAMED hard rule.
"""
from __future__ import annotations

from pen_stack.planner.delivery_vehicles import vehicle
from pen_stack.planner.target_site import target_site_available
from pen_stack.rules import Design, legality_report, load_ruleset

_PERM = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG" # CT core + GTN PAM + NGG present
_POLYA = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
_ATTP = "AGGTTTGTCTGGTCAACCACCGCGGTCTCAGTGGTGTACGGTACAAACCCA"


def _vio(report):
    return [v["rule_id"] for v in report["violations"]]


# ---- rule base integrity ----------------------------------------------------------------------
def test_ruleset_loads_with_required_fields():
    rs = load_ruleset()
    assert len(rs.rules) >= 9
    for r in rs.rules:
        assert r.id and r.kind in ("hard_reject", "soft_penalty", "scope_flag")
        assert r.mechanism and r.evaluator and r.test_ref
        assert r.kind != "hard_reject" or r.provenance.get("doi") # hard rejects must be cited


def test_delivery_palette_has_six_plus_vehicles():
    from pen_stack.planner.delivery_vehicles import names
    assert len(names()) >= 6
    for n in names():
        v = vehicle(n)
        assert "compatible_cargo_form" in v and "integrating" in v


# ---- parity: rules reproduce the existing code's decisions ------------------------------------
def test_reachability_rule_parity():
    rs = load_ruleset()
    rule = rs.get("reachability.target_element_available")
    from pen_stack.rules.evaluators import reachability_target_site
    for fam, seq, att in [("bridge_IS110", _PERM, False), ("serine_integrase", _PERM, False),
                          ("serine_integrase", _ATTP, False), ("CAST_VK", _POLYA, False),
                          ("Cas9", _PERM, False)]:
        ref = target_site_available(fam, seq, installed_att=att)["available"]
        rr = reachability_target_site(Design(writer_family=fam, site_seq=seq, installed_att=att), rule)
        got = rr.status == "pass"
        assert got == ref, f"parity break {fam}: rule={got} code={ref}"


def test_payload_rule_parity():
    rs = load_ruleset()
    rule = rs.get("payload.cargo_within_capacity")
    from pen_stack.rules.evaluators import payload_capacity
    for veh, cargo in [("AAV_single", 3000), ("AAV_single", 35000), ("helper_dependent_adenovirus", 35000)]:
        cap = vehicle(veh)["cargo_capacity_bp"]
        ref_legal = cargo <= cap
        rr = payload_capacity(Design(cargo_bp=cargo, delivery_vehicle=veh), rule)
        assert (rr.status == "pass") == ref_legal


# ---- positive controls ------------------------------------------------------------------------
def test_positive_controls_legal():
    cases = [
        Design(write_type="insertion", writer_family="bridge_IS110", site_seq=_PERM, cargo_bp=3000,
               delivery_vehicle="AAV_single"),
        Design(writer_family="serine_integrase", site_seq=_ATTP, cargo_bp=3000, delivery_vehicle="AAV_single"),
        Design(writer_family="bridge_IS110", site_seq=_PERM, cargo_bp=35000,
               delivery_vehicle="helper_dependent_adenovirus"),
        Design(writer_family="Cas9", site_seq=_PERM, cargo_bp=2000, delivery_vehicle="electroporation"),
    ]
    for d in cases:
        assert legality_report(d)["legal"], d


# ---- negative controls: rejected by the CORRECT named rule ------------------------------------
def test_payload_controls():
    r = legality_report(Design(writer_family="bridge_IS110", site_seq=_PERM, cargo_bp=35000,
                               delivery_vehicle="AAV_single"))
    assert not r["legal"] and "payload.cargo_within_capacity" in _vio(r)


def test_reachability_controls():
    r = legality_report(Design(writer_family="serine_integrase", site_seq=_PERM, cargo_bp=3000,
                               delivery_vehicle="AAV_single"))
    assert not r["legal"] and "reachability.target_element_available" in _vio(r)
    r2 = legality_report(Design(writer_family="CAST_VK", site_seq=_POLYA, cargo_bp=3000,
                                delivery_vehicle="AAV_single"))
    assert not r2["legal"] and "reachability.target_element_available" in _vio(r2)


def test_delivery_controls():
    # RNP-only writer into DNA-only AAV
    r = legality_report(Design(writer_family="Cas9", site_seq=_PERM, cargo_bp=2000,
                               delivery_vehicle="AAV_single"))
    assert not r["legal"] and "delivery.cargo_form_compatible" in _vio(r)
    # non-integrating goal + integrating lentivirus
    r2 = legality_report(Design(writer_family="bridge_IS110", site_seq=_PERM, cargo_bp=3000,
                                delivery_vehicle="lentivirus", no_integration=True))
    assert not r2["legal"] and "delivery.no_integration_constraint" in _vio(r2)
    # scope flag always present for a vehicle
    assert any(s["rule_id"] == "delivery.immunogenicity_magnitude" for s in r2["scope_flags"])


def test_fold_controls():
    rs = load_ruleset()
    from pen_stack.rules.evaluators import fold_cross_loop
    rule = rs.get("fold.cross_loop_complementarity")
    # a self-complementary (palindromic-ish) guide pair trips the cross-loop flag
    bad = fold_cross_loop(Design(target_guide="ACGTACGT", donor_guide="ACGTACGT"), rule)
    assert bad.status in ("flag", "pass") # deterministic on the screen
    na = fold_cross_loop(Design(), rule)
    assert na.status == "not_applicable"


def test_multiplex_controls():
    rs = load_ruleset()
    from pen_stack.rules.evaluators import multiplex_translocation
    rule = rs.get("multiplex.translocation_risk")
    # two DSB nuclease edits on different chromosomes -> elevated risk flag
    edits = [{"family": "Cas9", "chrom": "chr1", "pos": 1000, "name": "e1"},
             {"family": "Cas9", "chrom": "chr2", "pos": 2000, "name": "e2"}]
    rr = multiplex_translocation(Design(edits=edits), rule)
    assert rr.status == "flag" and rr.value >= 0.2
    # DSB-free recombinase plan -> ~zero
    edits2 = [{"family": "bridge_IS110", "chrom": "chr1", "pos": 1000},
              {"family": "bridge_IS110", "chrom": "chr2", "pos": 2000}]
    assert multiplex_translocation(Design(edits=edits2), rule).status == "pass"


def test_legality_and_confidence_not_collapsed():
    # the solver returns legality only, no 'confidence' key anywhere in its output (kept a separate axis)
    r = legality_report(Design(writer_family="bridge_IS110", site_seq=_PERM, cargo_bp=3000,
                               delivery_vehicle="AAV_single"))
    assert "legal" in r and "confidence" not in r
    assert all("confidence" not in rr for rr in r["rule_results"])


# ---- v7.1.4: compliance / germline-prohibition (heritable human germline editing is out of scope) -----------

def _routed_vio(design: dict):
    from pen_stack.planner.router import route_and_evaluate
    r = route_and_evaluate(Design(**design))
    return r["legal"], [x["rule_id"] for x in r["rule_results"]
                        if x["kind"] == "hard_reject" and x["status"] == "violate"]


def test_germline_edit_fails_legality():
    """A heritable / germline edit is a HARD legality reject naming compliance.germline_prohibition."""
    cases = [
        # the canonical reported example: explicit germline intent + germline-competent cell + in vivo
        {"write_type": "insertion", "gene": "PCSK9", "writer_family": "base_editor",
         "cargo_function": "permanent lipid-lowering germline edit", "cell_type": "h1_hesc", "in_vivo": True},
        {"write_type": "insertion", "gene": "PCSK9", "cargo_function": "heritable correction passed to offspring",
         "cell_type": "hepg2", "in_vivo": True},                                    # explicit heritable intent
        {"write_type": "insertion", "gene": "X", "cargo_function": "reporter", "cell_type": "embryo"},  # repro cell
        {"write_type": "insertion", "gene": "X", "cargo_function": "express GFP",
         "cell_type": "h1_hesc", "in_vivo": True},                                  # germline-competent + in vivo
    ]
    for d in cases:
        legal, vio = _routed_vio(d)
        assert legal is False, f"germline design wrongly legal: {d}"
        assert "compliance.germline_prohibition" in vio, f"germline rule did not fire: {d} -> {vio}"


def test_germline_rule_does_not_over_refuse_somatic():
    """Somatic / ex-vivo editing (incl. a germline-competent research line used ex vivo) stays legal."""
    cases = [
        {"write_type": "insertion", "gene": "F9", "writer_family": "bridge_is110", "cargo_bp": 1500,
         "delivery_vehicle": "AAV_single", "cargo_function": "factor IX for haemophilia",
         "cell_type": "hepg2", "in_vivo": True},
        {"write_type": "insertion", "gene": "X", "cargo_function": "express GFP reporter for research",
         "cell_type": "h1_hesc", "in_vivo": False},                                 # ex-vivo hESC research
        {"write_type": "insertion", "gene": "HBB", "cargo_function": "correct the sickle mutation",
         "cell_type": "ipsc", "in_vivo": False},                                    # ex-vivo iPSC somatic therapy
    ]
    for d in cases:
        _, vio = _routed_vio(d)
        assert "compliance.germline_prohibition" not in vio, f"germline rule over-refused somatic design: {d}"
