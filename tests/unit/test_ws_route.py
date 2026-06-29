"""WS-ROUTE unit tests (v3.3), write-type router. Pure-logic, CI-safe."""
from __future__ import annotations

from pen_stack.planner.router import load_write_types, route, route_and_evaluate
from pen_stack.rules import Design

_PERM = "ACGTGACCTAGGCTAGCTAGGTCAGCTAACTGGTCAGGTGCAGCTAGCTGACCTAGG"


def test_all_listed_write_types_route():
    for wt in load_write_types():
        r = route(Design(write_type=wt))
        assert r["supported"] and not r["deferred"]
        assert r["rule_categories"] and r["steps"]


def test_insertion_routes_to_insertion_subgraph():
    r = route(Design(write_type="insertion"))
    # compliance (germline-prohibition scope-of-use) applies to every write type (v7.1.4)
    assert set(r["rule_categories"]) == {"reachability", "fold", "payload", "delivery", "compliance"}
    assert "verify" in r["steps"]


def test_unsupported_write_type_defers():
    r = route(Design(write_type="teleportation"))
    assert not r["supported"] and r["deferred"] and "unsupported" in r["reason"]


def test_coverage_only_flagged():
    assert route(Design(write_type="excision"))["coverage_only"]
    assert not route(Design(write_type="insertion"))["coverage_only"]


def test_route_and_evaluate_runs_only_routed_categories():
    # multiplex routes to reachability+multiplex+delivery (NOT fold/payload)
    res = route_and_evaluate(Design(write_type="multiplex", writer_family="bridge_IS110", site_seq=_PERM,
                                    delivery_vehicle="electroporation",
                                    edits=[{"family": "bridge_IS110", "chrom": "chr1", "pos": 1},
                                           {"family": "bridge_IS110", "chrom": "chr2", "pos": 2}]))
    cats = {rr["category"] for rr in res["rule_results"]}
    assert cats <= {"reachability", "multiplex", "delivery", "compliance"}  # +compliance (v7.1.4)
    assert res["legal"] in (True, False) and not res["deferred"]


def test_deferred_write_type_returns_none_legal():
    res = route_and_evaluate(Design(write_type="nonsense"))
    assert res["deferred"] and res["legal"] is None
