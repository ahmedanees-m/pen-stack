"""The living world-model knowledge graph (v4.5, WS-G).

`pen_stack.graph` promotes the v4.0 flat tables (atlas / WT-KB / crosslink / delivery palette / write-type
taxonomy / GSH loci / documented writes / cell-type coverage cards) into a queryable knowledge graph: typed
nodes joined by typed edges, each carrying provenance + uncertainty + scope. Multi-hop design questions become
single grounded traversals; the gated living loop (`pen_stack.graph.ingest`) keeps it current without ever
auto-editing the curated truth.
"""
from __future__ import annotations

from pen_stack.graph.build import build_graph
from pen_stack.graph.query import (
    outcomes_for_writer,
    vehicles_for_writer,
    writers_for_locus,
    writers_reaching_and_deliverable,
)
from pen_stack.graph.schema import Edge, Graph, Node

__all__ = ["Graph", "Node", "Edge", "build_graph", "vehicles_for_writer", "writers_for_locus",
           "writers_reaching_and_deliverable", "outcomes_for_writer"]
