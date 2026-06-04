"""v3.1 WS-G - multiplex translocation-risk (G1) + guide ranking/QC (G2). CI-safe, pure-logic."""
from __future__ import annotations

from pen_stack.planner.multiplex import is_dsb_free, translocation_risk
from pen_stack.validate.guide_qc_demo import run as guide_demo


def _cas(name, chrom, pos, offt=None):
    return {"name": name, "family": "cas9", "chrom": chrom, "pos": pos, "offtargets": offt or []}


def test_dsb_free_plan_has_zero_translocation_risk():
    bridge = [{"name": "a", "family": "bridge_IS110", "chrom": "chr2", "pos": 1000},
              {"name": "b", "family": "seek_IS1111", "chrom": "chr11", "pos": 2000}]
    r = translocation_risk(bridge)
    assert r["all_dsb_free"] is True and r["n_cut_sites"] == 0 and r["translocation_risk"] == 0.0
    assert is_dsb_free("bridge_IS110") and not is_dsb_free("cas9")


def test_translocation_risk_is_monotonic():
    two = translocation_risk([_cas("e1", "chr2", 1000), _cas("e2", "chr11", 2000)])
    three = translocation_risk([_cas("e1", "chr2", 1000), _cas("e2", "chr11", 2000),
                                _cas("e3", "chr19", 3000)])
    assert three["translocation_risk"] >= two["translocation_risk"]      # more edits -> not lower
    # adding an off-target raises risk
    more_ot = translocation_risk([_cas("e1", "chr2", 1000, [{"chrom": "chr7", "pos": 5, "risk": 0.6}]),
                                  _cas("e2", "chr11", 2000)])
    assert more_ot["translocation_risk"] >= two["translocation_risk"]
    assert 0.0 <= two["translocation_risk"] <= 1.0 and two["band"] in {"low", "moderate", "high"}


def test_inter_chromosomal_join_is_not_below_intra():
    inter = translocation_risk([_cas("e1", "chr2", 1000), _cas("e2", "chr11", 1000)])
    intra_far = translocation_risk([_cas("e1", "chr2", 1000), _cas("e2", "chr2", 50_000_000)])
    assert inter["translocation_risk"] >= intra_far["translocation_risk"]


def test_qubo_is_optional_and_off_by_default():
    from pen_stack.planner.multiplex import qubo_baseline
    q = qubo_baseline([_cas("e1", "chr2", 1000)])
    assert q["enabled"] is False and "optional" in q["kind"].lower()


def test_multiplex_surfaced_in_agent_tools():
    from pen_stack.agent.tools import REGISTRY, dispatch
    assert "multiplex_translocation_risk" in REGISTRY
    r = dispatch("multiplex_translocation_risk",
                 {"edits": [_cas("e1", "chr2", 1000), _cas("e2", "chr11", 2000)]})
    assert r["tool"] == "planner.multiplex" and "translocation_risk" in r


def test_guide_qc_downranks_known_bad():
    r = guide_demo()
    assert r["best_is_good"] is True                 # the clean guide ranks first
    assert r["all_bad_below_good"] is True           # every known-bad guide ranks below it
    assert r["every_bad_flagged"] is True            # and is flagged


def test_guide_qc_flags_specific_failure_modes():
    from pen_stack.bridge.guide_qc import qc_flags
    palindrome = qc_flags("GCGCGCGCGCGCGCGCGCGC", "GACATCTACAAGGACATCGA")
    assert "self_complementarity" in palindrome["flags"] and palindrome["pass"] is False
    clean = qc_flags("ACAAGCTGGAAGAACTGAAG", "GACATCTACAAGGACATCGA")
    assert clean["pass"] is True
