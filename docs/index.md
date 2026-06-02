# PEN-STACK

**Open infrastructure for genome *writing*.** Editing tools tell you *how to change a base*. PEN-STACK
tells a genetic engineer *where* in the genome they can safely and durably write new information, and
*which enzyme* can write it there.

Three layers, one engine:

| Component | What it answers |
|---|---|
| **Writable Genome** (`pen_stack.wgenome`) | Where can I safely + durably insert DNA? (3M loci × cell type, learned blind) |
| **Writer Atlas** (`pen_stack.atlas` / `mech` / `score`) | What can write, and how well? (33,370 systems across 8 families, measured axes) |
| **Cross-link** (`pen_stack.atlas.crosslink`) | Which writers reach a locus / which loci a writer reaches |
| **Write Planner** (`pen_stack.planner`, Phase 3) | Find the optimal site × writer × cargo × delivery for a goal |

## Install

```bash
pip install pen-stack            # core
pip install 'pen-stack[server]'  # + REST API
pip install 'pen-stack[services]'  # + RAG / monitor / UI
```

## Quick start

```bash
pen-stack info                       # module map
pen-stack atlas --coverage           # Writer Atlas family coverage
pen-stack writable --gene CCR5       # rank writable loci near a gene
pen-stack crosslink --family bridge_IS110   # loci a writer family reaches
pen-stack monitor --back-test        # PEN-MONITOR living-database scan
```

REST API: `uvicorn pen_stack.server.api:app` → `GET /atlas/coverage`, `/crosslink/writers`, `/writable`, `/ask`.

Platform UI: `streamlit run pen_stack/ui/app.py`.

!!! warning "Decision-support, not a clinical directive"
    PEN-STACK returns calibrated risk / durability / reachability estimates. Tier-2/3 reachability is
    *candidate* and requires experimental validation. Verify all designs experimentally.

## Provenance

PEN-STACK consolidates five prior repositories (`genome-atlas`, `mech-class`, `pen-score`,
`pen-assemble`, `pen-compare`) into one citable monorepo. The audited 18-family Pfam whitelist (v1.2.1),
the multi-source mechanism classifier, the measured scoring axes, and the 1,058-entity curated universe
are carried forward; circular or unvalidatable claims were retired (see the v3.0 program document).
