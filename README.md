<div align="center">

# 🧬 PEN-STACK

### The Writable Genome — open infrastructure for genome *writing*

*Editing tools tell you **how** to change a base. PEN-STACK tells you **where** in the genome you can safely
and durably write new DNA — and **which enzyme** can write it there.*

[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-37e6e0.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.0.0a-3dffa2.svg)](CHANGELOG.md)
[![Code style: ruff](https://img.shields.io/badge/lint-ruff-FFC857.svg)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)
[![Pre-registered](https://img.shields.io/badge/validation-pre--registered-ff5d6c.svg)](prereg/)
[![Writable Genome](https://img.shields.io/badge/atlas-3M%20loci%20%C3%97%203%20cell%20types-9b59ff.svg)](#-the-writable-genome-paper-1-flagship)

</div>

---

## What is PEN-STACK?

PEN-STACK is a single, installable, **pre-registered** computational stack that builds the reference layer the
genome-**writing** era lacks. Genome *editing* changes a base in place; genome *writing* installs **new**
information — inserting genes, flipping or excising kilobases, placing landing pads. Two questions gate every
writing project and no resource answers them:

1. **Where can you write?** — a locus must accept an insert without disrupting an essential gene or activating
   an oncogene (**safety**), and the cargo must *stay expressed* (**durability**).
2. **What can write there, and how?** — which enzyme can physically reach the locus (**reachability**).

PEN-STACK answers both and joins them with an inverse-design **Write Planner**.

```
writability(locus) = safety  ×  durability  ×  reachability
                      │           │             │
        genotoxicity  │  will a   │  which writer enzyme
        risk (learned)│ cassette  │  can engage this site
                      │  stay on? │  (tiered, by family)
                      │ (learned) │
```

> **Headline result (Paper 1).** A genome-wide Writable Genome atlas (3,031,030 loci × **K562 / HepG2 / HSPC**)
> that recovers validated safe harbours as highly writable and clinical genotoxic loci as non-writable — **blind**:
> safe-harbour writability percentile ≈ **0.55–0.67** vs genotoxic-CIS ≈ **0.01–0.11** across all three cell types.
> Every pre-registered success criterion passes.

---

## How it works

PEN-STACK is organised as **two reference layers + one engine**, all built on bulk-downloadable public data and
validated against an honest baseline before release.

| Component | Module | Role | Status |
|---|---|---|---|
| 🟣 **Writable Genome** (flagship) | `pen_stack.wgenome` | learned per-locus safety × durability × reachability | ✅ Paper 1 |
| 🔵 **Writer Atlas** (companion) | `pen_stack.atlas`, `.mech`, `.score` | cross-family enzyme catalogue + Writer-Targeting KB | 🚧 Paper 2 |
| ⚙️ **Write Planner** (engine) | `pen_stack.planner` | inverse design: destination × writer × cargo × delivery | 🚧 Paper 3 |
| 🌉 **Bridge off-target engine** | `pen_stack.bridge` | "CRISPOR for bridge recombinases" (ships first) | 🚧 Paper 4 |
| 🛰️ Platform services | `monitor`, `rag`, `agent`, `ui`, `server` | living-DB, grounded RAG, agent/MCP, Streamlit UI, REST API | 🚧 / `ui` ✅ |

### The three learned layers (the flagship)

| Layer | Question | Supervision (public data) | Validation |
|---|---|---|---|
| **Safety** | will inserting here cause genotoxicity? | COSMIC Cancer Gene Census · DepMap essential genes · LaFave 2014 **3.7M MLV** integrations (K562/HepG2) · VISDB · chromatin | learned model *discriminates safe harbours* (AAVS1) where a naïve distance rule over-flags |
| **Durability** | will the cassette stay expressed? | **TRIP** position-effect data (Akhtar 2013, GSE49806/49807) → conditional `chromatin → expression` | Spearman ρ = **0.42**, silenced/stable AUROC **0.64**, beats the H3K9me3 baseline; transfers mouse → human |
| **Reachability** | which writer can engage it? | Writer-Targeting Knowledge Base (8 families, tiered) | Tier-1 sites recovered; Tier-2/3 flagged "requires validation" |

The durability model is *conditional on chromatin*, never on coordinates — so it transfers across cell types
(supply a cell type's epigenome and it scores that cell type). On the **CD34+ HSPC** partial panel (no ATAC), it
degrades gracefully and still validates — a built-in robustness result.

---

## 🔗 Connection to the prior PEN-STACK work

PEN-STACK v3.0 **consolidates and re-grounds** five earlier, separately published repositories. Their genuinely
reusable assets are imported here; the originals are archived read-only for provenance and DOI stability.

```
   genome-atlas ──┐  18-family InterPro-audited Pfam whitelist (v1.2.1)  ──►  WT-KB seed  (pen_stack/atlas)
   mech-class  ───┤  multi-source mechanism classifier                   ──►  reachability / family calls (pen_stack/mech)
   pen-score   ───┼─► 9 scoring axes (dsb/cargo/deliv/immuno/prog/…)      ──►  re-grounded axes (pen_stack/score)
   pen-assemble ──┤  IS110 ortholog / design set (1,029 entries)          ──►  part of the 1,058-entity universe
   pen-compare ───┘  unified_editor_universe.parquet (1,058) + scorecard  ──►  canonical universe + descriptive scorecard
                                                                                   (pen_stack/atlas/universe.py, scorecard.py)
```

| Prior repo | Pinned version | What v3.0 reuses | What changed |
|---|---|---|---|
| [`genome-atlas`](https://github.com/ahmedanees-m/genome-atlas) | v0.7.2 | the **audited 18-family Pfam backbone** → spine of the Writer-Targeting KB | GraphSAGE link-prediction framing retired |
| [`mech-class`](https://github.com/ahmedanees-m/mech-class) | v0.5.4 | the **mechanism classifier** (Pfam + RHEA + CRISPRcasdb + UniProt) | reused as the family/mechanism caller |
| [`pen-score`](https://github.com/ahmedanees-m/pen-score) | v0.1.3 | the **scoring axes** (`deliv`/`immuno`/`cargo`, …) | `prog`/`cargo` **re-grounded**; hand-set overrides removed |
| [`pen-assemble`](https://github.com/ahmedanees-m/pen-assemble) | v0.5.2 | the **ortholog sequence set** | de-novo chimera generation retired (0 validated writers) |
| [`pen-compare`](https://github.com/ahmedanees-m/pen-compare) | v0.1.0 | the **1,058-entity universe** + scorecard scaffold + tests | circular 5-gate "certification" → **descriptive scorecard** with *blind* concordance |

**One canonical assembly path** (`pen_stack/atlas/universe.py::assemble`) now feeds the classifier, the scorer,
and the scorecard identical metadata — the cross-module inconsistency in the prior pipelines cannot recur.

---

## Repository structure

```
pen-stack/
├── pen_stack/                      # the installable package
│   ├── wgenome/                    # 🟣 Writable Genome (Paper 1) — the flagship
│   │   ├── features.py             #    unified feature matrix (accessibility + histones + safety + integration)
│   │   ├── safety.py               #    calibrated genotoxicity-risk model (chrom-block CV + baseline)
│   │   ├── durability.py           #    conditional chromatin→expression model (TRIP-trained, transferable)
│   │   ├── writability.py          #    decomposable safety × durability × reachability integration
│   │   └── export_tracks.py        #    BigWig / BED atlas export
│   ├── atlas/                      # 🔵 Writer Atlas + WT-KB
│   │   ├── schema.py               #    pydantic WriterEntry (enforces ≥1 DOI per row)
│   │   ├── build_wtkb.py           #    Writer-Targeting Knowledge Base builder (8 families, tiered)
│   │   ├── universe.py             #    THE canonical universe assembly (1,058 entities)
│   │   └── scorecard.py            #    descriptive scorecard + blind concordance
│   ├── score/recalibrate.py        #    re-grounded scoring axes (no hand-set overrides)
│   ├── data/                       # ingestion (all public sources)
│   │   ├── genome.py  encode.py    #    hg38 grid · ENCODE REST resolver (no hard-coded accessions)
│   │   ├── ingest_chromatin.py     #    parallel ENCODE bigWig → 1 kb feature store
│   │   ├── ingest_safety_annot.py  #    COSMIC + DepMap + GENCODE → per-bin safety distances
│   │   ├── ingest_integration.py   #    LaFave MLV (hg19→hg38) + VISDB integration density
│   │   └── ingest_trip.py          #    TRIP durability supervision (GSE49806/49807, mm9)
│   ├── ui/app.py                   # 🛰️ Streamlit Writable Genome browser (6 pages, Plotly)
│   ├── mech/  planner/  bridge/    # Papers 2–4 (in progress)
│   ├── monitor/  rag/  agent/  server/   # platform services (in progress)
│   └── cli.py
├── scripts/                        # reproducible pipeline drivers (p1_*)
│   ├── p1_train_safety.py  p1_build_durability.py  p1_build_atlas.py
│   ├── p1_export_tracks.py  p1_validation_report.py  p1_safety_concordance.py
├── configs/                        # pinned datasets + thresholds + LLM + WT-KB curation (YAML)
│   ├── datasets.yaml  score_axes.yaml  wtkb_curated.yaml  universe_crosswalk.yaml  llm.yaml
├── prereg/                         # SHA-locked success criteria (paper1.yaml, phase0.yaml)
├── tests/unit/                     # 21 unit tests (schema, no-override, universe consistency, scorecard, smoke)
├── docker/                         # CUDA image + Phase-1 image (bio libs) + pinned requirements
├── tools/penctl.py                 # laptop↔VM orchestrator (paramiko SSH/SFTP, Docker-only)
├── docs/                           # INFRA, WT-KB table, scorecard results
└── pyproject.toml  CITATION.cff  CHANGELOG.md  LICENSE
```

> **Data policy.** Large artifacts (3 M-row atlases, BigWig tracks, models) are *not* committed — they are
> released via **Zenodo** (DOI) and reproducible from the public sources by re-running `scripts/p1_*`. Only small
> curated tables (the 1,058-entity universe, WT-KB) live in git.

---

## Data sources (all public, bulk-downloadable)

`hg38` (UCSC) · ENCODE bigWig signal (ATAC/DNase + 5 histone marks; K562, HepG2, CD34+ progenitor, mouse ES-Bruce4)
· GENCODE v46 · COSMIC Cancer Gene Census v104 · DepMap Public 26Q1 · LaFave 2014 (NHGRI GeIST) MLV integrations ·
VISDB · TRIP / Akhtar 2013 (GEO GSE49806/49807) · UniProt · Pfam/InterPro · Addgene. Every accession + DOI is
pinned in [`configs/datasets.yaml`](configs/datasets.yaml) and independently verified.

---

## Quick start

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"                 # core + tests
pip install -e ".[models,bio,server,services]"   # full stack (lightgbm, pyBigWig, fastapi, streamlit, …)
pytest -q                               # 21 tests
pen-stack info                          # stack status

# Explore the Writable Genome atlas (after fetching the Zenodo data release):
export PEN_ATLAS_DIR=/path/to/atlas_release
streamlit run pen_stack/ui/app.py       # forward/inverse queries, atlas browser, validation dashboard
```

**Reproduce Paper 1 from scratch** (heavy steps in Docker on a GPU VM, orchestrated by `penctl`):
```bash
python tools/penctl.py build                                  # build the image on the VM
penctl run python -m pen_stack.data.genome                    # 1 kb grid
penctl run python -m pen_stack.data.ingest_chromatin --biosample K562
penctl run python scripts/p1_train_safety.py --ct k562
penctl run python scripts/p1_build_atlas.py --ct k562         # → validated atlas
```

---

## The Streamlit browser

`pen_stack/ui/app.py` is a six-page scientific front-end over the atlas:

- **Forward query** — gene/coordinate → writability/safety/durability gauges + verdict + local track
- **Site finder (inverse)** — disease gene → top-N safest writable loci within a window (+ CSV)
- **Atlas browser** — genome-wide tracks · **Validation** — blind safe-harbour-vs-genotoxic recovery
- **Cross-cell-type** — K562 ↔ HepG2 transfer (reported honestly)

---

## Validation philosophy

- **Pre-register before training.** Success criteria, baselines and held-out sets are SHA-locked in `prereg/`
  before any model sees test data.
- **Always report an honest baseline** (oncogene-distance for safety; H3K9me3/LAD for durability).
- **Blind external concordance** — recover validated safe harbours, clinical genotoxic loci, measured activity.
- **Report failure honestly** — cross-cell-type degradation is a quantified result, not a footnote.

---

## Papers & phases

| # | Title | Phase | Status |
|---|---|---|---|
| **1** (flagship) | *The Writable Genome: a predictive, writer-aware atlas of safe & durable insertion sites* | 1 | ✅ atlas + validation complete |
| **2** (platform) | *PEN-STACK: unified open infrastructure for non-destructive genome writing* | 2 | 🚧 |
| **3** (capstone) | *The Write Planner: end-to-end inverse design of genomic writes* | 3 | 🚧 |
| **4** (beachhead) | *Genome-wide off-target prediction for RNA-guided bridge recombinases* | 1.5 | 🚧 |

---

## Citation

```bibtex
@software{penstack2026,
  author  = {Mahaboob Ali, Anees Ahmed},
  title   = {PEN-STACK: open infrastructure for genome writing (The Writable Genome)},
  year    = {2026},
  version = {3.0.0a},
  url     = {https://github.com/ahmedanees-m/pen-stack}
}
```

**Author:** Anees Ahmed Mahaboob Ali · VIT University, Vellore · MIT licensed.
*Decision-support, not a clinical directive — every score is traceable to public data + a pre-registered model.*
