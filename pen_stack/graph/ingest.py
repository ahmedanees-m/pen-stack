"""The gated living-ingestion loop (v4.5, WS-MON), the agent proposes; a gate disposes.

PEN-MONITOR (Europe PMC living scan) and agents emit **candidate** nodes/edges from new evidence. v4.5
Principle 1 is inviolable and encoded here: **no process auto-edits the curated world-model.** Candidates are
*quarantined*; the ONLY way one enters the graph is `gate_admit(...)` with (a) automated checks passing AND
(b) explicit approval. Every admission is versioned with date + evidence + the gate that admitted it
(auditable history, Principle 3).

There is deliberately no bulk-merge / auto-accept function: `propose(...)` only appends to the quarantine and
never receives a `Graph`, so it *cannot* mutate the graph (asserted by test).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Literal

from pen_stack.graph.schema import Edge, Graph, Node

CandidateKind = Literal["node", "edge"]
Status = Literal["quarantined", "admitted", "rejected"]


@dataclass
class Candidate:
    kind: CandidateKind
    payload: dict[str, Any] # a Node-like or Edge-like dict
    provenance: dict[str, Any] # MUST carry a source + (doi or europepmc id)
    evidence: str = "predicted" # measured / curated / predicted
    status: Status = "quarantined"
    note: str | None = None


@dataclass
class Quarantine:
    """Holds candidates; NEVER holds or touches a Graph. The only sink for `propose`."""
    items: list[Candidate] = field(default_factory=list)

    def propose(self, c: Candidate) -> None:
        c.status = "quarantined" # forced; a proposal is never pre-approved
        self.items.append(c)

    def pending(self) -> list[Candidate]:
        return [c for c in self.items if c.status == "quarantined"]


def automated_checks(c: Candidate) -> tuple[bool, list[str]]:
    """Gate stage 1: a candidate must be provenance-bearing + well-typed before a human can even approve it."""
    reasons = []
    prov = c.provenance or {}
    if not (prov.get("source") or prov.get("doi") or prov.get("europepmc")):
        reasons.append("no provenance (need source / doi / europepmc id)")
    if c.evidence not in ("measured", "curated", "predicted"):
        reasons.append(f"invalid evidence kind {c.evidence!r}")
    if c.kind == "node" and not (c.payload.get("id") and c.payload.get("type")):
        reasons.append("node payload missing id/type")
    if c.kind == "edge" and not all(c.payload.get(k) for k in ("src", "dst", "etype")):
        reasons.append("edge payload missing src/dst/etype")
    return (not reasons), reasons


def gate_admit(graph: Graph, candidate: Candidate, *, approved: bool, admitted_by: str,
               log: list[dict] | None = None) -> dict:
    """The ONLY path a candidate enters the curated graph. Requires automated checks AND explicit approval;
    records a versioned admission. Returns the decision record; the graph is mutated ONLY on admit."""
    log = log if log is not None else []
    ok, reasons = automated_checks(candidate)
    decision = {"date": _dt.date.today().isoformat(), "kind": candidate.kind,
                "payload_id": candidate.payload.get("id") or candidate.payload.get("etype"),
                "evidence": candidate.evidence, "provenance": candidate.provenance,
                "automated_checks_passed": ok, "approved": bool(approved), "admitted_by": admitted_by}
    if not (ok and approved):
        candidate.status = "rejected"
        decision["admitted"] = False
        decision["reasons"] = reasons or ["not approved by gate"]
        log.append(decision)
        return decision
    # admit
    if candidate.kind == "node":
        graph.add_node(Node(id=candidate.payload["id"], type=candidate.payload["type"],
                            props=candidate.payload.get("props", {})))
    else:
        graph.add_edge(Edge(src=candidate.payload["src"], dst=candidate.payload["dst"],
                            etype=candidate.payload["etype"], evidence=candidate.evidence,
                            confidence=candidate.payload.get("confidence"),
                            scope=candidate.payload.get("scope"), provenance=candidate.provenance))
    candidate.status = "admitted"
    decision["admitted"] = True
    log.append(decision)
    return decision


# --------------------------------------------------------------------------------------------------
# back-test: surface a KNOWN recent addition as a candidate (deterministic / CI-safe, no network)
# --------------------------------------------------------------------------------------------------
def back_test_candidates() -> list[Candidate]:
    """The pre-registered back-test fixture: the recently-published bridge system **ISPpu10** (Europe PMC
    PPR1218813; bioRxiv 2026-03-19), which the live monitor surfaces. Proposed as a candidate writer node +
    a `performs insertion` edge, to be admitted only through the gate."""
    prov = {"source": "PEN-MONITOR Europe PMC", "europepmc": "PPR1218813",
            "doi": "10.64898/2026.03.19.712850", "date": "2026-03-19"}
    return [
        Candidate(kind="node", evidence="predicted", provenance=prov,
                  payload={"id": "writer:ISPpu10", "type": "writer",
                           "props": {"family": "bridge_IS110", "system": "ISPpu10",
                                     "output_form": "DNA", "note": "structure-gated bridge recombinase"}}),
        Candidate(kind="edge", evidence="predicted", provenance=prov,
                  payload={"src": "writer:ISPpu10", "dst": "write_type:insertion", "etype": "performs",
                           "scope": "coverage_only (newly reported; not yet human-cell measured)"}),
    ]


def propose_from_monitor(since: str = "2026-01-01", back_test: bool = False) -> Quarantine:
    """Run PEN-MONITOR and quarantine its hits as candidates (live path; network-guarded). The back-test
    path is deterministic. Candidates are ALWAYS quarantined, never merged here."""
    q = Quarantine()
    if back_test:
        for c in back_test_candidates():
            q.propose(c)
        return q
    try:
        from pen_stack.monitor.run import run_monitor
        rep = run_monitor(since=since)
        for row in rep.get("queue", []) if isinstance(rep, dict) else []:
            q.propose(Candidate(kind="node", evidence="predicted",
                                provenance={"source": "PEN-MONITOR", "doi": row.get("doi"),
                                            "europepmc": row.get("id")},
                                payload={"id": f"writer:{row.get('name', 'candidate')}", "type": "writer",
                                         "props": row}))
    except Exception: # noqa: BLE001 - network/Europe PMC absent -> empty quarantine, never fabricates
        pass
    return q
