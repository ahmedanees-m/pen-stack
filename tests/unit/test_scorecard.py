"""Descriptive scorecard + blind concordance (Step 0.5)."""
from pen_stack.atlas.scorecard import (
    T_DSB_DEPENDENT,
    T_ESTABLISHED,
    blind_concordance,
    ranking_stability,
    scorecard,
)
from pen_stack.atlas.universe import assemble


def _sc():
    return scorecard(assemble())


def test_scorecard_runs_on_full_universe():
    sc = _sc()
    assert len(sc) == 1058
    assert {"tier", "S_composite", "evidence_count"}.issubset(sc.columns)


def test_dsb_dependent_editor_is_demoted():
    sc = _sc().set_index("entity_id")
    assert sc.loc["SpCas9", "tier"] == T_DSB_DEPENDENT      # fails necessary DSB-free gate


def test_established_writer_reached_without_overrides():
    # ISCro4 should reach the top descriptive tier from generic re-grounded axes alone
    sc = _sc().set_index("entity_id")
    assert sc.loc["ISCro4", "tier"] == T_ESTABLISHED


def test_blind_concordance_bridge_top_is_iscro4():
    res = blind_concordance(_sc(), family="bridge_IS110", expected_top="ISCro4")
    # reported, not asserted as an input: ISCro4 tops the bridge family via cell-based evidence
    assert res["matches"] is True
    assert res["n"] >= 2


def test_ranking_stability_is_high():
    frac = ranking_stability(assemble(), family="bridge_IS110", expected_top="ISCro4", n=200)
    assert frac >= 0.5
