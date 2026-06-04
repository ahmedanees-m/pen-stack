<div align="center">

# PEN-STACK

### The Writable Genome - open infrastructure for genome *writing*

*Editing tools tell you **how** to change a base. PEN-STACK tells you **where** in the genome you can safely
and durably write new DNA, **which enzyme** can write it there, and **how** to design the write end-to-end.*

[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![coverage](https://raw.githubusercontent.com/ahmedanees-m/pen-stack/main/.github/badges/coverage.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ahmedanees-m/pen-stack/branch/main/graph/badge.svg)](https://codecov.io/gh/ahmedanees-m/pen-stack)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-115%20passing-success.svg)](tests/)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-purple.svg)](https://github.com/astral-sh/ruff)
[![Runtime: Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)
[![Validation: pre-registered](https://img.shields.io/badge/validation-pre--registered-critical.svg)](prereg/)
[![Genome-Writing Bench v0.1](https://img.shields.io/badge/benchmark-Genome--Writing%20Bench%20v0.1-6f42c1.svg)](benchmarks/genome_writing_bench/)

**Built on five prior, separately published repositories:**

[![genome-atlas](https://img.shields.io/badge/built_on-genome--atlas-1f6feb.svg)](https://github.com/ahmedanees-m/genome-atlas)
[![mech-class](https://img.shields.io/badge/built_on-mech--class-1f6feb.svg)](https://github.com/ahmedanees-m/mech-class)
[![pen-score](https://img.shields.io/badge/built_on-pen--score-1f6feb.svg)](https://github.com/ahmedanees-m/pen-score)
[![pen-assemble](https://img.shields.io/badge/built_on-pen--assemble-1f6feb.svg)](https://github.com/ahmedanees-m/pen-assemble)
[![pen-compare](https://img.shields.io/badge/built_on-pen--compare-1f6feb.svg)](https://github.com/ahmedanees-m/pen-compare)

</div>

---

## What is PEN-STACK?

PEN-STACK is a single, installable, pre-registered computational stack that builds the reference and design
layer the genome-**writing** era lacks. It consolidates five earlier research projects into one citable
package, then adds the two reference maps and the design engine the field was missing.

Genome **editing** changes a base or short stretch in place. Genome **writing** installs *new* information -
inserting genes, flipping or excising kilobases, placing programmable landing pads. Writing is the harder,
less-tooled, and more clinically transformative modality, and it is gated by questions that today have no
canonical answer.

## The problem, and the gaps PEN-STACK closes

Two questions gate every genome-writing project, and before PEN-STACK no resource answered them together:

| Gap | The problem today | What PEN-STACK provides |
|---|---|---|
| **Where can you write?** | Each lab re-derives an ad-hoc "safe harbour" shortlist from inconsistent criteria; published lists range from ~2,000 sites to 25, none predict expression durability from a learned model, none are writer-aware, most cover one cell type. | **The Writable Genome** - a learned, cell-type-aware, writer-aware atlas scoring every locus for *safety* (genotoxicity risk) x *durability* (will the cassette stay expressed) x *reachability* (which enzyme can engage it). |
| **What can write there, and how well?** | Enzyme capabilities are scattered across papers; no catalogue places all genome-writing families on common, measured axes with their targeting requirements. | **The Writer Atlas** - 33,370 enzyme systems across 8 families on common measured axes, joined to the Writable Genome by a bidirectional cross-link. |
| **How do I design the actual write?** | Destination, enzyme, cargo and delivery are interdependent and goal-dependent; no tool optimises them jointly. | **The Write Planner** - inverse design that, given a goal and an `edit_intent`, returns ranked, traceable site x writer x cargo x delivery plans. |
| **Where might my bridge-recombinase design go off-target?** | Bridge recombinases are the most programmable writers, but had no genome-wide off-target screening tool (a "CRISPOR" equivalent); their developers list this as future work. | **The bridge off-target engine** (`pen-bridge`) - measured-data-validated screening that *nominates and ranks candidate off-target locations* (a screen, not a per-site risk calculator). |

Everything is built on bulk-downloadable public data, runs on a single GPU, and is validated **blind** against
a pre-registered, honest baseline before release.

## What is new in v3.1

v3.1 hardens the honesty of the planning benchmark, surrounds the models with strong baselines, adds a
predicted-structure safety axis, and ships the first benchmark and grounded agent for the genome-*writing*
side of the field. Every workstream is pre-registered (`prereg/ws_*.yaml`, SHA-locked) and reports its
honest negatives, not just its wins.

| Workstream | What it adds | Honest headline result |
|---|---|---|
| **A - De-circularized benchmark** (gate) | retires the circular targeted-intent recovery@k; the headline is now blind safe-harbour discovery | blind GSH discovery **AUROC 0.92** vs safety-only 0.50 |
| **B - Strong baselines + safety metric switch** | endogenous-expression baseline, multi-mark ablation, published GSH rule-set; safe-harbour discrimination is now the primary safety metric | learned writability **0.92 (95% CI 0.82-0.98)** vs GSH distance-rule 0.38 (delta CI excludes zero); the circular `genotoxic_cis` AUROC demoted to a labeled diagnostic |
| **C - AlphaGenome integration** | predicted sequence tracks + a predicted **3D structural-risk** axis (Hi-C contact-map deltas) via the hosted AlphaGenome API | per-track transfers well (HepG2 ATAC 0.91), but the *composite* score degrades from predicted tracks, so the measured atlas stays the backbone (flagged) |
| **D - Cargo Polish** | scores the *insert* for silencing/instability triggers (CpG islands, GC, cryptic splice, MFE, silencers) | directional: high-CpG bacterial cassette 0.75 vs CpG-depleted 0.0, every flag carries a fix |
| **E - Genome-Writing Bench v0.1 + PEN-Agent** | the first benchmark for the writing side, plus a grounded agent that cannot fabricate | planner beats the naive baseline 3/3; a real LLM agent reaches the planner's numbers only by grounding (0 fabricated) |
| **F - Local recalibration / private-data adaptation** | recalibrate or fine-tune the released models on your own assays, in-container, behind a validation gate | the adapted model activates only if it beats the released model AND a no-skill baseline; the released model is provably unchanged |
| **G - Multiplex + guide QC** | a pairwise translocation-risk screen for multi-edit plans, and a bridge-RNA guide ranker | DSB-free recombinase plans carry ~zero translocation risk by construction; known-bad guides are retrospectively down-ranked |

The **Genome-Writing Bench** (workstream E) is v3.1's adoption vehicle: a one-command, SHA-locked, leaderboard
benchmark with deterministic scorers and no circular labels. See
[`benchmarks/genome_writing_bench/`](benchmarks/genome_writing_bench/) and `docs/positioning.md`.

## Architecture

```
                           +-------------------------------------------+
                           |            WRITE PLANNER (engine)         |
                           |   inverse design: destination x writer    |
                           |   x cargo/guide x delivery -> ranked plan  |
                           +----------------^-------------^-------------+
                                            |             |
                  +-------------------------+--+      +---+------------------------+
                  |    WRITABLE GENOME (B)     |      |      WRITER ATLAS (A)      |
                  |    flagship reference      |<---->|   companion reference      |
                  |                            | reach|                            |
                  |  - Safety layer (learned)  | ability  - Family targeting KB    |
                  |  - Durability layer (learned)|      |  - Measured scoring axes   |
                  |  - Reachability layer  -----+------+  - Mechanism classifier    |
                  |  -> writability profile    |      |  - DMS variant model        |
                  +-------------------------^--+      +---+------------------------+
                                            |             |
         +----------------------------------+-------------+-------------------------+
         |                       DATA FOUNDATION (bulk-downloadable)                |
         |  hg38 . ENCODE/Roadmap chromatin . Hi-C/LADs . TRIP position effects .   |
         |  RID/VISDB/MLV integration sites . clinical genotoxic CIS . COSMIC .     |
         |  DepMap . gnomAD . GTEx . UniProt . Pfam/InterPro . bridge-recombinase   |
         |  off-target + DMS (Perry 2025)                                           |
         +-------------------------------------------------------------------------+

   Platform services (on top of the validated core): PEN-MONITOR (Europe PMC living database),
   grounded RAG/Q&A, a tool-using agent + MCP server, and a Streamlit web app.
```

## How it works

PEN-STACK is organised as **two reference layers + one engine + a services layer**.

| Component | Module | Role | Status |
|---|---|---|---|
| **Writable Genome** (flagship) | `pen_stack.wgenome` | learned per-locus safety x durability x reachability | Paper 1 |
| **Writer Atlas** (companion) | `pen_stack.atlas`, `.mech`, `.score` | cross-family enzyme catalogue + Writer-Targeting KB | Paper 2 |
| **Cross-link** | `pen_stack.atlas.crosslink` | bidirectional writer to locus queries | Paper 2 |
| **Write Planner** (engine) | `pen_stack.planner` | inverse design, `edit_intent`-conditioned | Paper 3 |
| **Agentic platform** | `pen_stack.agent` | goal to cited, auditable plan; MCP server; one-command deploy | Paper 3 |
| **Bridge off-target engine** | `pen_stack.bridge` | "CRISPOR for bridge recombinases" + guide QC (v3.1) | Paper 4 |
| **Genome-Writing Bench** (v3.1) | `benchmarks/`, `bench/run.py` | first writing-side benchmark; deterministic scorers, leaderboard | M2 |
| **PEN-Agent** (v3.1) | `pen_stack.agent.pen_agent` | grounded write-planning state machine; zero fabrication | M2 |
| **3D structural risk** (v3.1) | `pen_stack.wgenome.structure3d` | AlphaGenome contact-map deltas as a safety axis | M1 |
| **Cargo Polish** (v3.1) | `pen_stack.planner.cargo_polish` | cargo-sequence silencing-risk scan | M1 |
| **Local adaptation** (v3.1) | `pen_stack.adapt` | gated recalibration / fine-tuning on private data | M1 |
| **Multiplex risk** (v3.1) | `pen_stack.planner.multiplex` | pairwise translocation-risk screen for multi-edit plans | M3 |
| **Platform services** | `monitor`, `rag`, `ui`, `server` | living database, grounded RAG, web app, REST API | - |

### Headline results (all blind / pre-registered)

- **Paper 1 (Writable Genome):** a genome-wide atlas of 3,031,030 loci x 3 cell types (K562, HepG2, CD34+
  HSPC) recovers validated safe harbours as highly writable and clinical genotoxic loci as non-writable,
  blind. Durability transfers mouse to human (Spearman rho = 0.42).
- **Paper 2 (Writer Atlas):** 33,370 enzyme systems across 8 families on common measured axes; mechanism
  classifier agrees with the audited labels on the curated core (1.00); cross-link validated on AAVS1.
- **Paper 3 / v3.1 (Write Planner + de-circularized benchmark):** the honest headline is **blind
  safe-harbour site discovery** - run genome-wide (so no on-target identity term fires), the planner's
  writability separates held-out, DOI-validated safe harbours from matched-context controls at **AUROC
  0.92** (safety-only baseline 0.50). Writer-family recovery@1 = 1.0 vs prevalence 0.25 across 4 families.
  The earlier "recovery@10 = 1.00, McNemar p" result for *targeted* intents was definitional, not
  predictive (an on-target identity term dominates the score), so it is now reported only as a
  specification-compliance correctness table - see `docs/benchmark_circularity.md`. A tool-using agent
  never fabricates a number (every value traces to a validated tool call).
- **Paper 4 (Bridge off-target engine):** to our knowledge the first measured-data-validated tool that
  **nominates and ranks candidate off-target *locations*** for bridge recombinases. On the measured Perry
  2025 data (6,856 real off-targets) the per-position profile confirms the central core (positions 7-9) is
  the specificity determinant, and the model ranks real off-targets above core-disrupted decoys at AUROC
  0.77 vs 0.62 for Hamming. Stated plainly: it is a **screening tool, not a quantitative safety
  calculator**, it does not quantify how much recombination occurs at each site (sequence-risk vs measured
  magnitude, rho approximately 0.30). A first-of-its-kind beachhead for a genuinely unoccupied gap, not a
  Nature-tier breakthrough; the Writable Genome (Paper 1) remains the flagship novelty.

## The Genome-Writing Bench (v3.1, M2)

The first benchmark for the **writing** side of genome engineering - *where* to write, *what* writer to use,
*how* to design the cargo, and *what off-target / structural risk* a write carries - complementing the many
editing-side (Cas9 / base / prime) benchmarks. Six tasks, each with a deterministic scorer and a documented
ground-truth source; **no task is scored against a circular label** (it inherits the de-circularization gate).

```bash
python bench/run.py --agent          # one command -> out/bench_results.json + a leaderboard
docker compose run --rm bench python bench/run.py --agent   # same, on the clean image
```

| Solver | Beats naive on | No-fabrication | Note |
|---|---|---|---|
| deterministic planner | 3/3 grounded tasks | n/a | the validated planning tools (reference) |
| naive baseline | - | n/a | safety-only / prevalence / Hamming |
| **LLM agent** (PEN-Agent) | = planner (grounded) | **PASS** | a real LLM drives the tools; reaches the planner only by grounding every value, 0 fabricated |

Per-task (planner vs naive): site selection **0.92** vs 0.50, writer recovery **1.0** vs 0.25, off-target
**0.77** vs 0.62, intent 7/7, no-fabrication **PASS** (a hard gate). **PEN-Agent** (`pen_stack.agent`) is a
grounded write-planning state machine - goal to site to writer to cargo (with Cargo Polish) to off-target
to 3D structural risk to report - that copies every number from a validated tool with provenance and refuses
or degrades rather than invent. See [`benchmarks/genome_writing_bench/`](benchmarks/genome_writing_bench/),
`docs/agent.md`, and the leaderboard submission guide.

## How PEN-STACK connects to the prior repositories

PEN-STACK v3.0 consolidates and re-grounds five earlier projects. Their genuinely reusable assets are
imported here; the originals are archived read-only for provenance and DOI stability. This is what makes
PEN-STACK "the thing you cite instead of rebuilding the pipeline."

```
  genome-atlas  --+  18-family InterPro-audited Pfam whitelist (v1.2.1)  -->  WT-KB + mechanism classifier
  mech-class  ----+  multi-source mechanism classifier                   -->  family / mechanism calls
  pen-score  -----+- 9 scoring axes (dsb/cargo/deliv/immuno/prog/...)     -->  re-grounded therapeutic axes
  pen-assemble  --+  IS110 ortholog / design set                         -->  part of the 1,058-entity universe
  pen-compare  ---+  unified_editor_universe.parquet (1,058) + scorecard  -->  canonical universe + scorecard
```

| Prior repo | Pinned version | What v3.0 reuses | What changed |
|---|---|---|---|
| [genome-atlas](https://github.com/ahmedanees-m/genome-atlas) | v0.7.2 | the audited 18-family Pfam backbone - spine of the WT-KB and the at-scale mechanism classifier | GraphSAGE link-prediction framing retired |
| [mech-class](https://github.com/ahmedanees-m/mech-class) | v0.5.4 | the mechanism classifier (Pfam + RHEA + CRISPRcasdb + UniProt) | reused as the family/mechanism caller |
| [pen-score](https://github.com/ahmedanees-m/pen-score) | v0.1.3 | the scoring axes (deliv / immuno / cargo, ...) | prog/cargo re-grounded; hand-set overrides removed |
| [pen-assemble](https://github.com/ahmedanees-m/pen-assemble) | v0.5.2 | the ortholog sequence set | de-novo chimera generation retired -> DMS-grounded point-variant proposal |
| [pen-compare](https://github.com/ahmedanees-m/pen-compare) | v0.1.0 | the 1,058-entity universe + scorecard scaffold + tests | circular 5-gate "certification" -> descriptive scorecard with blind concordance |

**One canonical assembly path** (`pen_stack/atlas/universe.py::assemble`) feeds the classifier, the scorer,
and the scorecard identical metadata, so the cross-module inconsistency in the prior pipelines cannot recur.

## Repository structure

```
pen-stack/
├── pen_stack/                        the installable package
│   ├── wgenome/                      Writable Genome (Paper 1)
│   │   ├── features.py               unified feature matrix (accessibility + histones + safety + integration)
│   │   ├── safety.py                 calibrated genotoxicity-risk model (chrom-block CV + baseline)
│   │   ├── durability.py             conditional chromatin->expression model (TRIP-trained, transferable)
│   │   ├── writability.py            decomposable safety x durability x reachability integration
│   │   └── export_tracks.py          BigWig / BED atlas export
│   ├── atlas/                        Writer Atlas + WT-KB + cross-link (Papers 1-2)
│   │   ├── schema.py                 pydantic WriterEntry (enforces >=1 DOI per row)
│   │   ├── build_wtkb.py             Writer-Targeting Knowledge Base builder (8 families, tiered)
│   │   ├── expand.py                 ortholog ingestion -> atlas.parquet (33,370 systems)
│   │   ├── crosslink.py              writers_for_locus / loci_for_writer / loci_for_gene
│   │   ├── variant_propose.py        DMS-grounded point-mutation proposal (no chimeras)
│   │   ├── universe.py               THE canonical universe assembly (1,058 entities)
│   │   └── scorecard.py              descriptive scorecard + blind concordance
│   ├── mech/                         mechanism classification at scale (audited 18-family whitelist v1.2.1)
│   ├── score/                        re-grounded axes + therapeutic-readiness scoring
│   ├── planner/                      Write Planner (Paper 3): optimize / cargo / cargo_polish / multiplex / pipeline
│   ├── bridge/                       bridge off-target engine (Paper 4): offtarget / fold_qc / guide_qc / pipeline / cli
│   ├── agent/                        agentic platform: tools / orchestrator / pen_agent / mcp_server / guardrails
│   ├── adapt/                        local recalibration / private-data adaptation behind a gate (v3.1, WS-F)
│   ├── monitor/                      PEN-MONITOR living database (Europe PMC)
│   ├── rag/                          grounded, cited Q&A (hybrid LLM: Ollama primary, Nemotron fallback)
│   ├── validate/                     benchmarks: blind_gsh_discovery / durability_baselines / seq_vs_measured / agent_eval / adapt_demo
│   ├── data/                         ingestion (genome, chromatin, integration, TRIP, safety annotations)
│   ├── server/api.py                 FastAPI REST (atlas, crosslink, writable, plan, bridge, ask)
│   ├── ui/app.py                     Streamlit web app (11 pages)
│   └── cli.py                        unified CLI
├── benchmarks/genome_writing_bench/  Genome-Writing Bench v0.1 (tasks / harness / solvers / LEADERBOARD / SHAs)
├── bench/run.py                      one-command bench entrypoint (--agent, --verify)
├── scripts/                          reproducible pipeline drivers (p1_*, p2_*, p4_*, ws_*_report)
├── configs/                          pinned datasets + thresholds + curation (YAML)
├── prereg/                           SHA-locked success criteria (paper1..4 + ws_a..ws_g + locks)
├── data/curated/                     small committed tables (universe, gene coords, measured bridge profile)
├── tests/unit/                       unit + regression + blind-validation suite
├── docs/                             mkdocs site (cards, tutorials, INFRA, DEPLOY, MCP)
├── docker/                           CUDA image + UI image + pinned requirements
├── tools/penctl.py                   laptop<->VM orchestrator (paramiko SSH/SFTP, Docker-only)
├── docker-compose.yml                one-command self-hostable platform
└── pyproject.toml  CITATION.cff  CHANGELOG.md  LICENSE
```

> **Data policy.** Large artifacts (3 M-row atlases, BigWig tracks, models) and any third-party copyrighted
> data are *not* committed - they are released via Zenodo (DOI) or fetched from the original source, and are
> reproducible by re-running the scripts. Only small curated tables and derived products live in git.

## Installation and quick start

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"                                   # core + tests
pip install -e ".[models,bio,bridge,server,services]"     # full stack
pytest -q                                                 # 115 tests
pen-stack info                                            # stack status
python bench/run.py --agent                               # run the Genome-Writing Bench (under 5 min)
```

A five-minute quickstart that runs a bench task end-to-end is in [`docs/quickstart.md`](docs/quickstart.md).

Query the stack:

```bash
pen-stack atlas --coverage                                # Writer Atlas coverage (33,370 systems x 8 families)
pen-stack writable --gene CCR5 --ct k562                  # rank writable loci near a gene
pen-stack crosslink --chrom chr19 --bin 55090             # which writers reach AAVS1
pen-stack plan --gene TRAC --intent knock_in_with_disruption --cargo-bp 2000   # inverse-design plans
pen-bridge design --target ACGTGTCTACGTGA --donor TTGCATCTAGGCAC               # bridge design + off-target + QC
pen-stack monitor --back-test                             # PEN-MONITOR living-database scan
```

Self-host the whole platform (API + web app + agent + MCP + LLM), one command:

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:7b-instruct   # first run only (local fallback model)
# Web app :8501  .  API :8000 (/plan, /bridge/design, /ask)  .  MCP :8765   (see docs/DEPLOY.md)
```

**LLM backend (hybrid, non-load-bearing).** Services (agent, RAG, PEN-MONITOR) use one switch in
`configs/llm.yaml`. On the compute tier (the GPU VM) the default is the **local Ollama model**
(`qwen2.5:7b-instruct`, free, private, tool-calling verified) with **automatic fallback** to the hosted
**NVIDIA Nemotron** (free, no local resources), then to a deterministic no-LLM path. A cooldown cache and
bounded timeouts mean an absent or slow provider degrades in seconds rather than stalling. The LLM is
non-load-bearing - every number and citation comes from a validated tool - so the choice never affects
scientific reproducibility, only orchestration quality. Set `NVIDIA_API_KEY` (or a gitignored
`configs/nvidia_api_key.txt`) for the hosted fallback; a low-RAM laptop with no GPU uses it automatically.
The core scientific compute uses no LLM at all.

## The web platform

`pen_stack/ui/app.py` is a single Streamlit app over the whole stack (11 pages):

- **Writable Genome** - Overview, Forward query (gene to writability/safety/durability), Site finder
  (inverse), Atlas browser, Validation dashboard, Cross-cell-type transfer.
- **Writer Atlas** - family coverage and measured-axis comparison.
- **Write Planner** - goal + `edit_intent` to ranked, traceable plans.
- **Bridge design** - design a bridge RNA, fold/cross-loop QC, genome-wide off-target scan.
- **Ask** - grounded, cited Q&A (numbers from validated tools).
- **Agent** - a goal to a cited, auditable end-to-end plan.

## Data sources (all public)

hg38 (UCSC); ENCODE / Roadmap chromatin (ATAC/DNase + histone marks; K562, HepG2, CD34+ progenitor, mouse
ES-Bruce4); GENCODE v46; COSMIC Cancer Gene Census v104; DepMap Public 26Q1; LaFave 2014 (NHGRI GeIST) MLV
integrations; VISDB; TRIP / Akhtar 2013 (GEO GSE49806/49807); UniProt orthologs; Pfam/InterPro; Europe PMC;
Addgene; Perry 2025 bridge-recombinase off-target + DMS data (Science adz0276; copyrighted - kept local,
only derived products released). Every accession and DOI is pinned in `configs/datasets.yaml` and
independently verified.

## Validation philosophy

- **Pre-register before training.** Success criteria, baselines and held-out sets are SHA-locked in
  `prereg/` (paper1..4) before any model sees test data.
- **Always report an honest baseline** (oncogene-distance for safety; H3K9me3/LAD for durability;
  intent-blind ranking for the Planner; Hamming for the bridge engine).
- **Blind external concordance** - recover validated safe harbours, clinical genotoxic loci, documented
  writes, and measured off-targets the model never trained on.
- **Report failure honestly** - cross-cell-type degradation, small benchmark N, and the limits of
  sequence-only off-target magnitude prediction are quantified results, not footnotes.
- **Grounded services** - every quantitative answer comes from a validated tool call (never a language
  model); the living database never auto-edits the atlas; clinical directives are refused.

## Papers and phases

| # | Title | Phase | Status |
|---|---|---|---|
| 1 (flagship) | The Writable Genome: a predictive, writer-aware atlas of safe & durable insertion sites | 1 | complete |
| 2 (platform) | PEN-STACK: unified open infrastructure for non-destructive genome writing | 2 | complete |
| 3 (capstone) | The Write Planner: end-to-end inverse design of genomic writes | 3 | complete |
| 4 (beachhead) | Genome-wide off-target prediction for RNA-guided bridge recombinases | 1.5 | complete |
| M1 (v3.1) | Writable Genome hardened: strong baselines, AlphaGenome sequence + 3D structural-risk axis | v3.1 B,C,D,F | complete |
| M2 (v3.1) | The Genome-Writing Bench + PEN-Agent: the writing-side benchmark and a grounded agent | v3.1 E | complete |
| M3 (v3.1) | Multiplex translocation-risk + bridge-RNA guide QC | v3.1 G | complete |

The v3.1 cycle (workstreams A-H) is recorded in `CHANGELOG.md`, `docs/positioning.md`, and the SHA-locked
`prereg/ws_*.yaml`; preprint drafts are in `manuscripts/`.

Per-phase build records, execution summaries, and Zenodo deposit packages are kept alongside the program
plan. Data releases are deposited on Zenodo (one per paper).

## Citation

```bibtex
@software{penstack2026,
  author  = {Mahaboob Ali, Anees Ahmed},
  title   = {PEN-STACK: open infrastructure for genome writing (The Writable Genome)},
  year    = {2026},
  version = {3.1.0},
  url     = {https://github.com/ahmedanees-m/pen-stack}
}
```

**Author:** Anees Ahmed Mahaboob Ali, VIT University, Vellore. MIT licensed.

*Decision-support, not a clinical directive - every score is traceable to public data and a pre-registered
model.*
