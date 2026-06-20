"""The living world-model knowledge graph, schema (v4.5, WS-G).

The substrate's ground truth (L3) was flat tables joined by code. v4.5 promotes it to a queryable
**knowledge graph**: typed nodes (writer / locus / cargo / vehicle / cell_type / write_type / outcome) joined
by typed edges (reaches / deliverable_by / performs / durable_in / carries / used_writer / observed_at), where
**every edge carries its provenance, its uncertainty, and the scope within which it holds** (v4.5 Principle 2).

Edges are typed by evidence kind, `measured` (a documented experimental outcome) > `curated` (a
hand-verified fact, e.g. a delivery-vehicle property) > `predicted` (a model/homology inference), so an
agent traversing the graph always knows how much to trust each hop. Nodes/edges are plain dataclasses; the
store (build/query) is pure-Python + JSON/sqlite (Docker-friendly, no graph-DB dependency).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

NodeType = Literal["writer", "locus", "cargo", "vehicle", "cell_type", "write_type", "outcome"]
EdgeType = Literal["reaches", "deliverable_by", "performs", "durable_in", "carries",
                   "used_writer", "observed_at"]
EvidenceKind = Literal["measured", "curated", "predicted"]


@dataclass
class Node:
    id: str
    type: NodeType
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Edge:
    src: str
    dst: str
    etype: EdgeType
    evidence: EvidenceKind # measured / curated / predicted (trust ordering)
    confidence: float | None = None # [0,1] where known; None = not quantified (abstain)
    scope: str | None = None # the context within which the edge holds (limit)
    provenance: dict[str, Any] = field(default_factory=dict) # {source, doi, date, ...}

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def key(self) -> tuple:
        return (self.src, self.dst, self.etype)


class Graph:
    """An in-memory typed multigraph with provenance-tagged edges. Pure Python; serialises to JSON."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._adj: dict[str, list[Edge]] = {} # src -> edges (built lazily)

    # ---- construction --------------------------------------------------------------------------
    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.src not in self.nodes or edge.dst not in self.nodes:
            raise KeyError(f"edge {edge.key} references an unknown node")
        self.edges.append(edge)
        self._adj.setdefault(edge.src, []).append(edge)

    # ---- traversal -----------------------------------------------------------------------------
    def out_edges(self, node_id: str, etype: EdgeType | None = None) -> list[Edge]:
        es = self._adj.get(node_id, [])
        return [e for e in es if etype is None or e.etype == etype]

    def neighbors(self, node_id: str, etype: EdgeType | None = None) -> list[str]:
        return [e.dst for e in self.out_edges(node_id, etype)]

    def nodes_of(self, ntype: NodeType) -> list[Node]:
        return [n for n in self.nodes.values() if n.type == ntype]

    # ---- serialisation -------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"nodes": [n.to_dict() for n in self.nodes.values()],
                "edges": [e.to_dict() for e in self.edges]}

    @classmethod
    def from_dict(cls, d: dict) -> "Graph":
        g = cls()
        for n in d["nodes"]:
            g.add_node(Node(**n))
        for e in d["edges"]:
            g.add_edge(Edge(**e))
        return g

    def summary(self) -> dict:
        from collections import Counter
        return {"n_nodes": len(self.nodes), "n_edges": len(self.edges),
                "nodes_by_type": dict(Counter(n.type for n in self.nodes.values())),
                "edges_by_type": dict(Counter(e.etype for e in self.edges)),
                "edges_by_evidence": dict(Counter(e.evidence for e in self.edges))}
