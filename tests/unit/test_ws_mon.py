"""WS-MON unit tests (Phase 4.5) - the gated living-ingestion loop. The hard gate (Principle 1): no process
auto-edits the curated world-model; candidates are quarantined and admitted only through the gate. CI-safe
(back-test fixture is deterministic; no network)."""
from __future__ import annotations

from pen_stack.graph import build_graph
from pen_stack.graph.ingest import (
    Candidate,
    Quarantine,
    automated_checks,
    back_test_candidates,
    gate_admit,
    propose_from_monitor,
)


def test_proposing_does_not_touch_the_graph():
    g = build_graph()
    n0, e0 = len(g.nodes), len(g.edges)
    q = propose_from_monitor(back_test=True)
    assert len(q.pending()) >= 1 # candidates were proposed
    assert len(g.nodes) == n0 and len(g.edges) == e0 # ... but the graph is UNCHANGED
    # Quarantine has no access to a Graph at all (Principle 1 enforced structurally)
    assert not hasattr(Quarantine(), "graph")


def test_gate_rejects_unprovenanced_or_unapproved_candidates():
    g = build_graph()
    n0 = len(g.nodes)
    # (a) no provenance -> automated checks fail -> rejected, graph unchanged
    bad = Candidate(kind="node", provenance={}, payload={"id": "writer:X", "type": "writer"})
    ok, reasons = automated_checks(bad)
    assert not ok and reasons
    d = gate_admit(g, bad, approved=True, admitted_by="tester")
    assert d["admitted"] is False and len(g.nodes) == n0
    # (b) well-formed + provenanced but NOT approved -> still rejected
    good = back_test_candidates()[0]
    d2 = gate_admit(g, good, approved=False, admitted_by="tester")
    assert d2["admitted"] is False and len(g.nodes) == n0


def test_gate_admits_backtest_addition_with_versioned_record():
    g = build_graph()
    n0, e0 = len(g.nodes), len(g.edges)
    log: list[dict] = []
    cands = back_test_candidates() # ISPpu10 node + performs edge
    for c in cands:
        gate_admit(g, c, approved=True, admitted_by="human:curator", log=log)
    assert "writer:ISPpu10" in g.nodes # admitted into the curated graph
    assert len(g.nodes) == n0 + 1 and len(g.edges) == e0 + 1
    assert all(d["admitted"] and d["date"] and d["provenance"].get("europepmc") == "PPR1218813"
               for d in log) # every admission versioned with date + evidence
    assert all(c.status == "admitted" for c in cands)


def test_no_auto_edit_path_exists():
    # the only graph-mutating ingestion entrypoint is gate_admit; propose/back_test never mutate a graph.
    import inspect

    from pen_stack.graph import ingest
    # propose_from_monitor / back_test_candidates must not add nodes/edges to a Graph
    assert "add_node" not in inspect.getsource(ingest.propose_from_monitor)
    assert "add_edge" not in inspect.getsource(ingest.back_test_candidates)
    # gate_admit is the sole admitter and is gated on `approved`
    assert "approved" in inspect.signature(gate_admit).parameters
