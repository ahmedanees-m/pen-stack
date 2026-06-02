<div align="center">

# 🧬 PEN-STACK

### The Writable Genome — open infrastructure for genome *writing*

*Editing tools tell you **how** to change a base. PEN-STACK tells you **where** in the genome you can safely
and durably write new DNA — and **which enzyme** can write it there.*

[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-37e6e0.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.0.0a3-3dffa2.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-46%20passing-3dffa2.svg)](tests/)
[![Code style: ruff](https://img.shields.io/badge/lint-ruff-FFC857.svg)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)
[![Pre-registered](https://img.shields.io/badge/validation-pre--registered-ff5d6c.svg)](prereg/)
[![Writable Genome](https://img.shields.io/badge/atlas-3M%20loci%20%C3%97%203%20cell%20types-9b59ff.svg)](#-the-writable-genome-paper-1--flagship)
[![Writer Atlas](https://img.shields.io/badge/writer%20atlas-33%2C370%20systems%20%C3%97%208%20families-37e6e0.svg)](#-the-writer-atlas--unified-stack-paper-2)

</div>

---

## What is PEN-STACK?

PEN-STACK is a single, installable, **pre-registered** computational stack that builds the reference layer the
genome-**writing** era lacks. Genome *editing* changes a base in place; genome *writing* installs **new**
information — inserting genes, flipping or excising kilobases, placing landing pads. Two questions gate every
writing project, and no resource answered them together:

1. **Where can you write?** — a locus must accept an insert without disrupting an essential gene or activating
   an oncogene (**safety**), and the cargo must *stay expressed* (**durability**).
2. **What can write there, and how?** — which enzyme can physically reach the locus, with what cargo, and
   how deliverably (**reachability** + the **Writer Atlas**).

PEN-STACK answers both and joins them with an inverse-design **Write Planner**.

```
writability(locus) = safety  ×  durability  ×  reachability
                      │           │             │
        genotoxicity  │  will a   │  which writer enzyme
        risk (learned)│ cassette  │  can engage this site
                      │  stay on? │  (tiered, by family) ──► Writer Atlas (33,370 systems)
                      │ (learned) │
```

> **Headline results.**
> **Paper 1 (Writable Genome):** a genome-wide atlas (3,031,030 loci × **K562 / HepG2 / HSPC**) recovers
> validated safe harbours as highly writable and clinical genotoxic loci as non-writable — *blind*.
> **Paper 2 (Writer Atlas):** **33,370 genome-writing enzyme systems across 8 families** on common measured
> axes, joined to the Writable Genome by a bidirectional **writer↔locus cross-link**.

---

## How it works

PEN-STACK is organised as **two reference layers + one engine + a services layer**, all built on
bulk-downloadable public data and validated against an honest baseline before release.

| Component | Module | Role | Status |
|---|---|---|---|
| 🟣 **Writable Genome** (flagship) | `pen_stack.wgenome` | learned per-locus safety × durability × reachability | ✅ **Paper 1** |
| 🔵 **Writer Atlas** (companion) | `pen_stack.atlas`, `.mech`, `.score` | cross-family enzyme catalogue + Writer-Targeting KB | ✅ **Paper 2** |
| 🔗 **Cross-link** | `pen_stack.atlas.crosslink` | bidirectional writer ↔ locus queries | ✅ Paper 2 |
| ⚙️ **Write Planner** (engine) | `pen_stack.planner` | inverse design: destination × writer × cargo × delivery | 🚧 Paper 3 |
| 🌉 **Bridge off-target engine** | `pen_stack.bridge` | "CRISPOR for bridge recombinases" (ships first) | 🚧 Paper 4 |
| 🛰️ **Platform services** | `monitor`, `rag`, `agent`, `ui`, `server` | living-DB, grounded RAG, agent/MCP, Streamlit UI, REST API | ✅ monitor / rag / ui / server · 🚧 agent |

### The three learned layers (the flagship — Paper 1)

| Layer | Question | Supervision (public data) | Validation |
|---|---|---|---|
| **Safety** | will inserting here cause genotoxicity? | COSMIC Cancer Gene Census · DepMap essential genes · LaFave 2014 **3.7M MLV** integrations (K562/HepG2) · VISDB · chromatin | learned model *discriminates safe harbours* (AAVS1) where a naïve distance rule over-flags |
| **Durability** | will the cassette stay expressed? | **TRIP** position-effect data (Akhtar 2013, GSE49806/49807) → conditional `chromatin → expression` | Spearman ρ = **0.42**, silenced/stable AUROC **0.64**, beats the H3K9me3 baseline; transfers mouse → human |
| **Reachability** | which writer can engage it? | Writer-Targeting Knowledge Base (8 families, tiered) | Tier-1 sites recovered; Tier-2/3 flagged "requires validation" |

### The Writer Atlas + cross-link (Paper 2)

| Capability | Module | Result |
|---|---|---|
| **Writer Atlas** — every family on measured axes | `atlas/expand.py` → `atlas.parquet` | **33,370 systems × 8 families** (31,885 IS110 orthologs); every row confidence-tagged + ≥1 DOI |
| **Mechanism at scale** — homology→mechanism | `mech/whitelist.py`, `classify_atlas.py` | audited 18-family Pfam whitelist v1.2.1; **core agreement 1.00** |
| **Therapeutic readiness** | `score/therapeutic.py` | deliverability / cargo / human-cell axes, components retained |
| **Cross-link** — writer ↔ Writable Genome | `atlas/crosslink.py` | AAVS1 (*PPP1R12C*) scores **0.90 writability** and is bridge-reachable |
| **Variant proposal** (DMS-grounded) | `atlas/variant_propose.py` | point mutations only (no chimeras); model plugs in at Phase 1.5 |
| **PEN-MONITOR** — living database | `monitor/` | Europe PMC scan; back-test **surfaces ISPpu10**; never auto-edits the atlas |
| **Grounded RAG / Q&A** | `rag/`, `agent/guardrails.py` | numbers from tool calls, claims cited, clinical directives refused |

The durability model is *conditional on chromatin*, never on coordinates — so it transfers across cell types
(supply a cell type's epigenome and it scores that cell type). On the **CD34+ HSPC** partial panel (no ATAC),
it degrades gracefully and still validates — a built-in robustness result.

---

## 🔗 Connection to the prior PEN-STACK work

PEN-STACK v3.0 **consolidates and re-grounds** five earlier, separately published repositories. Their
genuinely reusable assets are imported here; the originals are archived read-only for provenance and DOI
stability.

```
   genome-atlas ──┐  18-family InterPro-audited Pfam whitelist (v1.2.1)  ──►  WT-KB + mech classifier (pen_stack/atlas, /mech)
   mech-class  ───┤  multi-source mechanism classifier                   ──►  family / mechanism calls (pen_stack/mech)
   pen-score   ───┼─► 9 scoring axes (dsb/cargo/deliv/immuno/prog/…)      ──►  re-grounded axes (pen_stack/score)
   pen-assemble ──┤  IS110 ortholog / design set (1,029 entries)          ──►  part of the 1,058-entity universe
   pen-compare ───┘  unified_editor_universe.parquet (1,058) + scorecard  ──►  canonical universe + descriptive scorecard
```

| Prior repo | Pinned version | What v3.0 reuses | What changed |
|---|---|---|---|
| [`genome-atlas`](https://github.com/ahmedanees-m/genome-atlas) | v0.7.2 | the **audited 18-family Pfam backbone** → spine of the WT-KB *and* the at-scale mechanism classifier | GraphSAGE link-prediction framing retired |
| [`mech-class`](https://github.com/ahmedanees-m/mech-class) | v0.5.4 | the **mechanism classifier** (Pfam + RHEA + CRISPRcasdb + UniProt) | reused as the family/mechanism caller |
| [`pen-score`](https://github.com/ahmedanees-m/pen-score) | v0.1.3 | the **scoring axes** (`deliv`/`immuno`/`cargo`, …) | `prog`/`cargo` **re-grounded**; hand-set overrides removed |
| [`pen-assemble`](https://github.com/ahmedanees-m/pen-assemble) | v0.5.2 | the **ortholog sequence set** | de-novo chimera generation retired → DMS-grounded point-variant proposal |
| [`pen-compare`](https://github.com/ahmedanees-m/pen-compare) | v0.1.0 | the **1,058-entity universe** + scorecard scaffold + tests | circular 5-gate "certification" → **descriptive scorecard** with *blind* concordance |

**One canonical assembly path** (`pen_stack/atlas/universe.py::assemble`) feeds the classifier, the scorer,
and the scorecard identical metadata — the cross-module inconsistency in the prior pipelines cannot recur.

---

## Repository structure

```
pen-stack/
├── pen_stack/                        # the installable package
│   ├── wgenome/                      # 🟣 Writable Genome (Paper 1) — the flagship
│   │   ├── features.py               #    unified feature matrix (accessibility + histones + safety + integration)
│   │   ├── safety.py                 #    calibrated genotoxicity-risk model (chrom-block CV + baseline)
│   │   ├── durability.py             #    conditional chromatin→expression model (TRIP-trained, transferable)
│   │   ├── writability.py            #    decomposable safety × durability × reachability integration
│   │   └── export_tracks.py          #    BigWig / BED atlas export
│   ├── atlas/                        # 🔵 Writer Atlas + WT-KB + cross-link (Papers 1–2)
│   │   ├── schema.py                 #    pydantic WriterEntry (enforces ≥1 DOI per row)
│   │   ├── build_wtkb.py             #    Writer-Targeting Knowledge Base builder (8 families, tiered)
│   │   ├── expand.py                 #    🆕 ortholog ingestion → atlas.parquet (33,370 systems × 8 families)
│   │   ├── crosslink.py              #    🆕 writers_for_locus / loci_for_writer / loci_for_gene
│   │   ├── variant_propose.py        #    🆕 DMS-grounded point-mutation proposal (no chimeras)
│   │   ├── universe.py               #    THE canonical universe assembly (1,058 entities)
│   │   ├── scorecard.py              #    descriptive scorecard + blind concordance
│   │   └── atlas.parquet             #    the Writer Atlas (committed; large data via Zenodo)
│   ├── mech/                         # 🆕 mechanism classification at scale
│   │   ├── whitelist.py              #    audited 18-family Pfam whitelist v1.2.1 + composite rules
│   │   ├── classify_atlas.py         #    homology→mechanism (independent of inherited label) + review queue
│   │   └── pfam_whitelist.yaml       #    the 18-family table (imported from genome-atlas)
│   ├── score/                        # therapeutic-readiness scoring
│   │   ├── recalibrate.py            #    re-grounded axes (no hand-set overrides)
│   │   └── therapeutic.py            #    🆕 deliverability / cargo / human-cell readiness profile
│   ├── monitor/                      # 🆕 PEN-MONITOR living-database engine
│   │   ├── europepmc.py  triage.py  run.py     #    Europe PMC scan → human-reviewed curation queue
│   ├── rag/                          # 🆕 grounded, cited Q&A
│   │   ├── qa.py                     #    numbers from tool calls; claims cited; clinical directives refused
│   │   ├── index.py                  #    cited fact-card retriever over the atlas/WT-KB
│   │   └── llm.py                    #    optional Ollama/Qwen phrasing layer (presentation only)
│   ├── agent/guardrails.py           # 🆕 grounded / cited / defer-to-tools / decision-support contract
│   ├── server/api.py                 # 🆕 FastAPI REST (atlas, crosslink, writable, ask)
│   ├── ui/app.py                     # 🛰️ Streamlit platform UI (10 pages: Writable Genome + Writer Atlas + Ask + …)
│   ├── data/                         # ingestion (all public sources)
│   │   ├── genome.py  encode.py      #    hg38 grid · ENCODE REST resolver (no hard-coded accessions)
│   │   ├── ingest_chromatin.py       #    parallel ENCODE bigWig → 1 kb feature store
│   │   ├── ingest_safety_annot.py    #    COSMIC + DepMap + GENCODE → per-bin safety distances
│   │   ├── ingest_integration.py     #    LaFave MLV (hg19→hg38) + VISDB integration density
│   │   └── ingest_trip.py            #    TRIP durability supervision (GSE49806/49807, mm9)
│   ├── planner/  bridge/             #    Papers 3–4 (in progress)
│   └── cli.py                        #    unified CLI (info / atlas / writable / crosslink / monitor)
├── scripts/                          # reproducible pipeline drivers
│   ├── p1_*.py                       #    Paper-1: train safety, build durability/atlas, export, validate
│   └── p2_build_atlas.py             #    🆕 Paper-2: expand → mechanism → therapeutic readiness
├── configs/                          # pinned datasets + thresholds + LLM + curation (YAML)
│   ├── datasets.yaml  score_axes.yaml  wtkb_curated.yaml  universe_crosswalk.yaml  gates_v3.yaml
│   ├── atlas_families.yaml           # 🆕 UniProt family queries for the atlas
│   ├── monitor_queries.yaml          # 🆕 Europe PMC query terms for PEN-MONITOR
│   └── llm.yaml                      #    single LLM switch (Ollama + Qwen2.5-7B, Apache-2.0)
├── prereg/                           # SHA-locked success criteria
│   ├── phase0.yaml  paper1.yaml  SHA256_LOCK_phase0.json
│   └── paper2.yaml  SHA256_LOCK_phase2.json     # 🆕
├── tests/unit/                       # 46 unit tests (atlas, mech, therapeutic, crosslink, monitor, rag, …)
├── docs/                             # mkdocs site
│   ├── index.md  INFRA.md  REPRO.md  wtkb.md  scorecard.md
│   ├── cards/{safety,durability,atlas}.md       # model & data cards
│   └── tutorials/                    # 🆕 4 use-case tutorials (where-to-write, which-writer, compare, deliverability)
├── docker/                           # CUDA image + Phase-1 image (bio libs) + pinned requirements
├── tools/penctl.py                   # laptop↔VM orchestrator (paramiko SSH/SFTP, Docker-only)
├── mkdocs.yml                        # 🆕 docs site config
└── pyproject.toml  CITATION.cff  CHANGELOG.md  LICENSE
```

> **Data policy.** Large artifacts (3 M-row atlases, BigWig tracks, models, ortholog TSV caches) are *not*
> committed — they are released via **Zenodo** (DOI) and reproducible from public sources by re-running
> `scripts/p1_*` / `scripts/p2_build_atlas.py`. Only small curated tables (the 1,058-entity universe, WT-KB,
> and the 0.9 MB Writer Atlas) live in git.

---

## Data sources (all public, bulk-downloadable)

`hg38` (UCSC) · ENCODE bigWig signal (ATAC/DNase + 5 histone marks; K562, HepG2, CD34+ progenitor, mouse
ES-Bruce4) · GENCODE v46 · COSMIC Cancer Gene Census v104 · DepMap Public 26Q1 · LaFave 2014 (NHGRI GeIST)
MLV integrations · VISDB · TRIP / Akhtar 2013 (GEO GSE49806/49807) · **UniProt orthologs** (IS110, CAST,
serine integrase, Cas12a, TnpB) · Pfam/InterPro · **Europe PMC** (PEN-MONITOR) · Addgene. Every accession +
DOI is pinned in [`configs/datasets.yaml`](configs/datasets.yaml) and independently verified.

---

## Quick start

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"                          # core + tests
pip install -e ".[models,bio,server,services,docs]"   # full stack (lightgbm, pyBigWig, fastapi, streamlit, mkdocs, …)
pytest -q                                        # 46 tests
pen-stack info                                   # stack status
```

**Use the Writer Atlas (ships in the package):**
```bash
pen-stack atlas --coverage                       # family coverage (33,370 systems × 8 families)
pen-stack atlas --family bridge_IS110            # systems in a family
```

**Query the Writable Genome + cross-link** (after fetching the Zenodo atlas release):
```bash
export PEN_ATLAS_DIR=/path/to/atlas_release
pen-stack writable --gene CCR5 --ct k562         # rank writable loci near a gene
pen-stack crosslink --chrom chr19 --bin 55090    # which writers reach AAVS1
pen-stack monitor --back-test                    # PEN-MONITOR living-database scan (surfaces ISPpu10)
```

**REST API & web app:**
```bash
uvicorn pen_stack.server.api:app --port 8000     # GET /atlas/coverage /crosslink/* /writable /ask
streamlit run pen_stack/ui/app.py                # the full platform UI
```

**Reproduce from scratch** (heavy steps in Docker on a GPU VM, orchestrated by `penctl`):
```bash
python scripts/p2_build_atlas.py                 # Writer Atlas: expand → mechanism → readiness
python tools/penctl.py build                     # build the image on the VM (Paper 1 heavy steps)
penctl run python scripts/p1_build_atlas.py --ct k562
```

---

## The Streamlit platform UI

`pen_stack/ui/app.py` is the single web app over the whole stack:

- **Writable Genome** — Overview · Forward query (gene → writability/safety/durability gauges + verdict) ·
  Site finder (inverse) · Atlas browser · Validation dashboard · Cross-cell-type transfer.
- **Writer Atlas** — family coverage + measured-axis comparison across writer families.
- **Ask (RAG)** — grounded, cited Q&A; shows the tool provenance + citations + decision-support disclaimer.
- **Bridge design** (Phase 1.5) · **Write Planner** (Phase 3) — wired, pages staged.

---

## Validation philosophy

- **Pre-register before training.** Success criteria, baselines and held-out sets are SHA-locked in `prereg/`
  (`paper1.yaml`, `paper2.yaml`) before any model sees test data.
- **Always report an honest baseline** (oncogene-distance for safety; H3K9me3/LAD for durability).
- **Blind external concordance** — recover validated safe harbours, clinical genotoxic loci, known writers.
- **Report failure honestly** — cross-cell-type degradation is a quantified result, not a footnote.
- **Grounded services** — every quantitative answer is produced by a validated tool call (never an LLM
  guess); PEN-MONITOR never auto-edits the atlas; clinical directives are refused.

---

## Papers & phases

| # | Title | Phase | Status |
|---|---|---|---|
| **1** (flagship) | *The Writable Genome: a predictive, writer-aware atlas of safe & durable insertion sites* | 1 | ✅ atlas + validation complete |
| **2** (platform) | *PEN-STACK: unified open infrastructure for non-destructive genome writing* | 2 | ✅ Writer Atlas + cross-link + services complete |
| **3** (capstone) | *The Write Planner: end-to-end inverse design of genomic writes* | 3 | 🚧 next |
| **4** (beachhead) | *Genome-wide off-target prediction for RNA-guided bridge recombinases* | 1.5 | 🚧 ships first |

Per-phase build records: [`Final_Part_v3.0/phase_*/`](https://github.com/ahmedanees-m/pen-stack) (execution
summaries + build logs). Data releases: **Zenodo** (Paper 1 atlas; Paper 2 Writer Atlas).

---

## Citation

```bibtex
@software{penstack2026,
  author  = {Mahaboob Ali, Anees Ahmed},
  title   = {PEN-STACK: open infrastructure for genome writing (The Writable Genome + Writer Atlas)},
  year    = {2026},
  version = {3.0.0a3},
  url     = {https://github.com/ahmedanees-m/pen-stack}
}
```

**Author:** Anees Ahmed Mahaboob Ali · VIT University, Vellore · MIT licensed.
*Decision-support, not a clinical directive — every score is traceable to public data + a pre-registered model.*
