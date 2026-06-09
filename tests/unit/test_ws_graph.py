"""WS-G unit tests (Phase 4.5) - the world-model knowledge graph. Deterministic, CI-safe (built from the
committed curated tables; no network/model)."""
from __future__ import annotations

from pen_stack.graph import build_graph, vehicles_for_writer, writers_reaching_and_deliverable
from pen_stack.graph.schema import Graph


def test_graph_builds_with_typed_nodes_and_provenanced_edges():
    g = build_graph()
    s = g.summary()
    assert s["n_nodes"] > 50 and s["n_edges"] > 100
    assert set(s["nodes_by_type"]) == {"writer", "locus", "cargo", "vehicle", "cell_type",
                                       "write_type", "outcome"}
    # every edge carries an evidence kind + provenance
    for e in g.edges:
        assert e.evidence in ("measured", "curated", "predicted")
        assert isinstance(e.provenance, dict)
    # evidence-kind histogram present
    assert set(s["edges_by_evidence"]) <= {"measured", "curated", "predicted"}


def test_json_round_trip_is_lossless():
    g = build_graph()
    g2 = Graph.from_dict(g.to_dict())
    assert len(g2.nodes) == len(g.nodes) and len(g2.edges) == len(g.edges)


def test_deliverable_by_edges_match_the_verifier_cargo_form_legality():
    # PARITY: the graph's deliverable_by edges reproduce the v3.3 rule-grounded verifier (0 mismatches)
    from pen_stack.verify import verify
    fams = ["bridge_IS110", "Cas9", "serine_integrase", "Cas12a", "PE_integrase"]
    vehs = ["AAV_single", "lnp_mrna", "electroporation", "lentivirus", "AAV_dual"]
    for fam in fams:
        gveh = {v["vehicle"] for v in vehicles_for_writer(fam)}
        for veh in vehs:
            legal = verify(dict(write_type="insertion", writer_family=fam, cargo_bp=2000,
                                delivery_vehicle=veh)).legal
            assert (veh in gveh) == legal, f"parity mismatch {fam}/{veh}"


def test_multihop_query_is_grounded_and_provenanced():
    r = writers_reaching_and_deliverable("AAVS1", cargo_form="DNA")
    assert r["n_answers"] >= 1 and r["grounded"] is True and r["no_fabrication"] is True
    for a in r["answers"]:
        assert a["provenance_path"]                      # every answer carries its traversed edges
        assert all("evidence" in hop and "provenance" in hop for hop in a["provenance_path"])
        assert a["output_form"] == "DNA"                 # DNA-form writers only (RNP excluded for DNA cargo)


def test_reaches_edges_are_locus_level_predicted_and_scope_flagged():
    g = build_graph()
    reaches = [e for e in g.edges if e.etype == "reaches"]
    assert reaches and all(e.evidence == "predicted" for e in reaches)
    assert all("locus-level" in (e.scope or "") for e in reaches)   # honest scope on every reach edge
