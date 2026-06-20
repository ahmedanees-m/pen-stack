"""WS-CT unit tests (Phase 4.5) - cell-type expansion + coverage cards + OOD labelling + graceful
degradation. CI-safe (config-driven)."""
from __future__ import annotations

from pen_stack.graph import build_graph
from pen_stack.graph.cell_types import (
    cell_types,
    coverage_card,
    cross_cell_type_ood,
    degrade,
    tier_b_roadmap,
)


def test_tier_a_cell_types_are_graph_nodes_with_coverage_cards():
    g = build_graph()
    ct_nodes = {n.id.split(":", 1)[1] for n in g.nodes_of("cell_type")}
    for ct in ("iPSC", "primary_T_cell", "hepatocyte"):
        assert ct in ct_nodes and ct in cell_types()
        card = coverage_card(ct)
        assert card and card.get("coverage") in ("full", "partial", "none") and card.get("tracks")
        # the node carries the coverage card
        node = next(n for n in g.nodes_of("cell_type") if n.id == f"cell_type:{ct}")
        assert node.props.get("coverage") == card["coverage"]


def test_partial_coverage_degrades_gracefully_full_does_not():
    full = degrade(0.95, "K562") # full coverage -> not capped
    partial = degrade(0.95, "iPSC") # partial coverage -> capped at 0.6
    assert full["confidence"] == 0.95 and full["degraded"] is False
    assert partial["confidence"] <= 0.6 and partial["degraded"] is True
    assert partial["raw_confidence"] == 0.95 # raw reported alongside (honest, not hidden)


def test_cross_cell_type_is_ood_labelled_same_is_not():
    same = cross_cell_type_ood("K562", "K562")
    cross = cross_cell_type_ood("hepatocyte", "K562")
    assert same["ood"] is False and same["label"] == "in-distribution"
    assert cross["ood"] is True and "extrapolating" in cross["label"]


def test_tier_b_is_roadmap_only_not_scored_nodes():
    g = build_graph()
    ct_nodes = {n.id.split(":", 1)[1] for n in g.nodes_of("cell_type")}
    roadmap = {r["cell_type"] for r in tier_b_roadmap()}
    assert roadmap and roadmap.isdisjoint(ct_nodes) # Tier-B documented but NOT added as scored nodes
    assert all(r.get("blocker") for r in tier_b_roadmap())
