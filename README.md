# PEN-STACK

**Open infrastructure for genome *writing*** — the operating system for adding, inverting, excising and
landing-padding DNA, not another single-enzyme editing tool.

> Editing tools tell you *how to change a base*. Nothing tells a genetic engineer *where in the genome they
> can safely and durably write new information, and which enzyme can write it there.* PEN-STACK builds that
> missing reference layer — **the Writable Genome** — and the **Writer Atlas** of genome-writing enzymes that
> operate on it.

This is the unified v3.0 monorepo. It consolidates and re-grounds five prior repositories
(`genome-atlas`, `mech-class`, `pen-score`, `pen-assemble`, `pen-compare`) into one installable, citable stack.

## What it is

Three components, one install:

| Component | Role |
|---|---|
| **Writable Genome** (`pen_stack.wgenome`) | per-locus `writability = safety × durability × reachability` (flagship, Paper 1) |
| **Writer Atlas** (`pen_stack.atlas`, `.mech`, `.score`) | cross-family enzyme catalogue + Writer-Targeting Knowledge Base (Paper 2) |
| **Write Planner** (`pen_stack.planner`) | inverse design: destination × writer × cargo × delivery (Paper 3) |
| **Bridge off-target engine** (`pen_stack.bridge`) | "CRISPOR for bridge recombinases" (Paper 4, ships first) |

Plus a guard-railed services layer: PEN-MONITOR (`monitor`), grounded RAG (`rag`), agent + MCP (`agent`),
Streamlit UI (`ui`), and a REST API (`server`).

## Status

**v3.0.0a0 — Phase 0 (Harden the Writer Core).** See `docs/INFRA.md` for the laptop↔VM↔Drive toolchain and
`prereg/` for SHA-locked success criteria. Build progresses per the PEN-STACK v3.0 program (Phases 0 → 1.5 → 1 → 2 → 3).

## Install

```bash
pip install -e .            # core
pip install -e ".[models,bio,server,services,dev]"   # full stack
```

## Module layout

```
pen_stack/
  atlas/   mech/   score/      # Writer Atlas + WT-KB + scoring (Pillar A)
  wgenome/                     # Writable Genome: safety/durability/reachability (Pillar B)
  planner/                     # Write Planner (engine)
  bridge/                      # bridge off-target engine (beachhead)
  monitor/ rag/ agent/ ui/     # guard-railed platform services
  data/ validate/ server/      # ingestion · blind-validation harness · REST API
```

## Reproducibility & honesty

Every learned layer is compared against a simple baseline and validated **blind** against public truths
(validated safe harbours, clinical genotoxic loci, measured writer activity). Success criteria are
pre-registered and SHA-locked in `prereg/` before models see test data. Failures (e.g. cross-cell-type
degradation) are reported as results, not hidden.

## Author & citation

**Anees Ahmed Mahaboob Ali** (VIT University, Vellore). MIT licensed. See `CITATION.cff`.
