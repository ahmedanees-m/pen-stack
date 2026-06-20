# The living world-model graph (v4.5)

v4.5 promotes PEN-STACK's ground truth from flat tables joined by code into a queryable **knowledge graph**:
typed nodes joined by typed edges, where **every edge carries its provenance, its uncertainty, and the scope
within which it holds**. An agent answers a multi-hop design question as a single grounded traversal.

## Schema (`pen_stack/graph/schema.py`)

| Nodes | Edges | Edge evidence (trust order) |
|---|---|---|
| `writer`, `locus`, `cargo`, `vehicle`, `cell_type`, `write_type`, `outcome` | `reaches`, `deliverable_by`, `performs`, `durable_in`, `carries`, `used_writer`, `observed_at` | `measured` > `curated` > `predicted` |

Every `Edge` has `evidence`, `confidence` (or `None` = abstain), `scope`, and `provenance` (`source`, `doi`,
`date`, …). The store is pure-Python and serialises to JSON: Docker-friendly, no graph-DB dependency.

## Building it (`build.py`)

The graph is assembled **deterministically from the v4.0 curated tables**: the WT-KB writer families, the
8-vehicle delivery palette, the write-type taxonomy, the DOI-validated GSH loci, the documented writer panel,
and the cell-type coverage cards. **Parity-first**: the `deliverable_by` edges reproduce the v3.3
rule-grounded verifier's cargo-form legality exactly (0 mismatches, asserted by test) before any multi-hop
extension. Nothing here calls a network or a model.

## Querying it (`query.py`, REST `POST /graph/query`, MCP `graph_query`)

```python
from pen_stack.graph import writers_reaching_and_deliverable
r = writers_reaching_and_deliverable("AAVS1", cargo_form="DNA")
# -> {n_answers, answers:[{writer, output_form, vehicles, provenance_path:[...]}], grounded, no_fabrication}
```

Each answer is the **provenanced multi-hop path** the query traversed (writer →reaches→ locus, writer
→deliverable_by→ vehicle), so the result is grounded by construction. The flat atlas/crosslink joins remain as
graph *views* (`vehicles_for_writer`, `writers_for_locus`) for parity and fallback.

## Currency & cell-type coverage

- The graph stays current through a **gated living loop** (`pen_stack/graph/ingest.py`): PEN-MONITOR
  emits *candidate* edges from new literature; they are quarantined and admitted only through a
  validation/human gate, versioned with date + evidence. **No process auto-edits the curated truth.**
- Cell types are nodes with **coverage cards** (`configs/cell_types.yaml`): which tracks are available, and
  therefore how trustworthy a score is. Cross-cell-type queries are OOD-labelled (the v3.2 finding); partial
  cell types degrade gracefully and are labelled.

## Scope

A graph is **bookkeeping, not new biology**: its value is queryability, currency, and provenance, not a new
predictor. Reachability edges are *locus-level* and *predicted* (the per-site element check stays planner
work); outcome edges are documented-evidence links, not clinical guarantees.
