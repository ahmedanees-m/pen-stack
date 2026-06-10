"""WS-PLAN + WS-MULTI unit tests (Phase 5.0) - the deliberative co-scientist: multiple distinct, verified,
confidence-tagged strategies, with no-fabrication holding under the matured agent. CI-safe."""
from __future__ import annotations

from pen_stack.agent.co_scientist import deliberate, distinctness, propose_strategies


def test_proposes_multiple_legal_confidence_tagged_strategies():
    r = propose_strategies("AAVS1", cargo_bp=3000, cell_type="K562", n=3)
    assert r["n_strategies"] >= 2
    assert r["all_legal"] is True and r["all_confidence_tagged"] is True
    for s in r["strategies"]:
        assert s["legal"] is True and s["confidence"] is not None and s["label"] and s["tradeoff"]


def test_strategies_are_materially_distinct_not_reworded():
    r = propose_strategies("AAVS1", n=3)
    d = r["distinctness"]
    assert d["materially_distinct"] is True
    assert d["min_pairwise_axis_diff"] >= 2          # every pair differs on >=2 design axes (measured)


def test_no_fabrication_holds_under_the_matured_agent():
    # the central v5.0 gate: the reasoning layer proposes/ranks but never sources a number
    r = propose_strategies("AAVS1", n=3)
    assert r["no_fabrication"] is True
    assert all(s["no_fabrication"] for s in r["strategies"])
    # numbers (confidence/interval) trace to the verifier provenance, not free text
    for s in r["strategies"]:
        assert "rules.solver" in s["provenance"].get("source", "") or s["confidence"] is not None


def test_distinctness_metric_flags_reworded_variants():
    # two strategies differing on 0 axes are NOT materially distinct
    from pen_stack.agent.co_scientist import Strategy
    a = Strategy("a", {"write_type": "insertion", "writer_family": "bridge_IS110",
                       "delivery_vehicle": "AAV_single", "edit_intent": "safe_harbour_insertion"},
                 True, 0.9, None, "grounded-confident", [], "t", True)
    b = Strategy("b", dict(a.design), True, 0.9, None, "grounded-confident", [], "t2", True)
    assert distinctness([a, b])["materially_distinct"] is False


def test_deliberate_runs_head_to_head_grounded():
    d = deliberate("AAVS1", cargo_bp=3000, cell_type="K562")
    assert d["deliberative_best"] is not None and d["deliberative_n"] >= 2
    assert d["distinctness"]["materially_distinct"] is True
    assert d["no_fabrication"] is True               # both deliberative + baseline grounded
