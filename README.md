<div align="center">

# PEN-STACK

### The Writable Genome - open infrastructure for genome *writing*

*Editing tools tell you **how** to change a base. PEN-STACK tells you **where** in the genome you can safely
and durably write new DNA, **which enzyme** can write it there, and **how** to design the write end-to-end.*

[![PyPI](https://img.shields.io/pypi/v/pen-stack.svg)](https://pypi.org/project/pen-stack/)
[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![Publish](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml)
[![coverage](https://raw.githubusercontent.com/ahmedanees-m/pen-stack/main/.github/badges/coverage.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ahmedanees-m/pen-stack/branch/main/graph/badge.svg)](https://codecov.io/gh/ahmedanees-m/pen-stack)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-3.2.0-blue.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-176%20passing-success.svg)](tests/)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-purple.svg)](https://github.com/astral-sh/ruff)
[![Runtime: Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)
[![Validation: pre-registered](https://img.shields.io/badge/validation-pre--registered-critical.svg)](prereg/)
[![Genome-Writing Bench v0.2](https://img.shields.io/badge/benchmark-Genome--Writing%20Bench%20v0.2-6f42c1.svg)](benchmarks/genome_writing_bench/)

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

## What is new in v3.2 — a calibrated, self-aware co-scientist

v3.2 makes the genome-writing funnel **trustworthy**: every value the funnel returns now carries a calibrated
confidence, an extrapolation flag, and — where the biology is beyond any tool here — an explicit "out of
scope." The LLM may plan, but ideas pass through computable filters, and the system says *how much to trust
each number* and *where the edge of its knowledge is*. Every workstream is pre-registered
(`prereg/ws_{uq,ep,mc,ba}.yaml`, SHA-locked) and reports its honest negatives.

| Workstream | What it adds | Honest headline result |
|---|---|---|
| **UQ — calibrated uncertainty + OOD** | conformal prediction intervals / sets over the existing heads (no retraining), an out-of-distribution detector, and selective prediction | calibrated UQ is **useful on the expression axis**: the durability **expression interval covers 0.895** vs 0.90 nominal on held-out chromosomes (within tolerance) and **risk-coverage accuracy rises 0.739→0.930** under abstention. On the **silenced axis it is informative-in-name-only** at this N — the set covers 0.996 with mean size 1.93 of 2 (≈ the full label set), because the head is weak (we say so plainly). OOD fires strongly on a real **chromatin-state** shift (euchromatin→heterochromatin AUROC **0.98**) but is **weak across biological context** — K562→HSPC 0.72, K562→HepG2 0.65, even cross-species mESC→human **0.56** — because chromatin-mark distributions barely move across cell types/species; reported as a heuristic feature-space-novelty signal, not a guarantee |
| **EP — epistemic scope** | a three-tier status (grounded-confident / grounded-extrapolating / not-computable) on every output, plus a known-unknowns registry + scope matcher | out-of-scope probes deferred **1.0**, in-scope false-defer **0.0** (zero fabrication); the no-fabrication hard gate still holds. The unknown funnel (structure→phenotype, in-vivo immunogenicity, long-term durability, epistasis, polygenic, germline) is made *legible*, not closed |
| **MC — mechanistic filters** | a hard target-site/PAM/att-site reachability reject, vehicle-specific delivery-sequence penalties, and an off-target **energetics** model | positive+negative target-site controls 9/9 (a physically impossible writer–site pairing is rejected); off-target **energetics beats the 0.77 baseline at AUROC 0.88** on the comparable (core-disrupted) construction and ships as the default ranker — but a reviewer-driven re-run shows that gap is *mostly the core-penalisation artifact*: with the core held matched, the non-core substitution-identity gain is real but **modest (Δ≈0.04: 0.687 vs 0.646)**; both AUROCs carry a favourable-negative-set caveat |
| **BA — bench v0.2 + uncertainty-aware agent** | four trust tasks (T8 calibration, T9 selective prediction, T10 OOD honesty, T11 out-of-scope) + the agent emits confidence + epistemic status + abstains | the uncertainty-aware agent beats an over-confident baseline **4/4** on the trust tasks; the leaderboard now separates *trustworthy* agents, not just grounded ones |

Optional: a thin **Gymnasium environment interface** (`pen_stack/env/`, `[env]` extra) for agent-developer
interoperability — interface only, no RL superiority claimed. See `docs/uncertainty.md`, `docs/scope.md`,
`docs/mechanistic_constraints.md`.

## What is new in v3.1

v3.1 hardens the honesty of the planning benchmark, surrounds the models with strong baselines, adds a
predicted-structure safety axis, and ships the first benchmark and grounded agent for the genome-*writing*
side of the field. Every workstream is pre-registered (`prereg/ws_*.yaml`, SHA-locked) and reports its
honest negatives, not just its wins.

| Workstream | What it adds | Honest headline result |
|---|---|---|
| **A - De-circularized benchmark** (gate) | retires the circular targeted-intent recovery@k; the headline is now blind safe-harbour discovery, on a gold set scaled from 5 to 16 loci | blind GSH discovery on 16 curated loci: **AUROC 0.68 (95% CI 0.53-0.82)**; validated-only (N=8) **0.70 (CI 0.48-0.91, underpowered)** vs safety-only 0.51 - a weak, honestly-bounded signal (the 0.92-on-5 was fragile). The full Pellenz-2019 35-site set is also included as a separate exploratory tier and scores near chance (0.54) - the model does not over-rank weak computational candidates |
| **B - Strong baselines + safety metric switch** | endogenous-expression baseline, multi-mark ablation, published GSH rule-set; safe-harbour discrimination is the primary safety metric | headline is the learned model's **absolute** discrimination: writability AUROC **0.68 (95% CI 0.53-0.82, N=16)**. The published distance rule is reported as a *qualitative failure case*, not a delta to beat - it scores at/below chance (curated 0.51; validated-8 **0.48**) because validated harbours are **intragenic** (AAVS1/PPP1R12C, CCR5), so a "far-from-genes" prior mis-ranks them; the learned-minus-rule delta is kept only as a non-significant diagnostic. The circular `genotoxic_cis` AUROC is demoted to a labeled diagnostic |
| **C - AlphaGenome integration** | predicted sequence tracks + a predicted **3D structural-risk** axis (Hi-C contact-map deltas) via the hosted AlphaGenome API | per-track transfers well (HepG2 ATAC 0.91), but the *composite* score degrades from predicted tracks, so the measured atlas stays the backbone (flagged) |
| **D - Cargo Polish** | scores the *insert* for silencing/instability triggers (CpG islands, GC, cryptic splice, MFE, silencers) | directional: high-CpG bacterial cassette 0.75 vs CpG-depleted 0.0, every flag carries a fix |
| **E - Genome-Writing Bench v0.1 + PEN-Agent** | the first benchmark for the writing side, plus a grounded agent that cannot fabricate | planner beats the naive baseline 3/3; the grounded agent reaches the planner's numbers only by grounding (0 fabricated). **T7 ungrounded contrast**: the same models with no tools fabricate 100% of tool-only values under a naive prompt (qwen2.5:7b, Nemotron) - so the bench separates grounded from ungrounded agents, not just "did it call the tool" |
| **F - Local recalibration / private-data adaptation** | recalibrate or fine-tune the released models on your own assays, in-container, behind a validation gate | the adapted model activates only if it beats the released model AND a no-skill baseline; the released model is provably unchanged |
| **G - Multiplex + guide QC** | a pairwise translocation-risk screen for multi-edit plans, and a bridge-RNA guide ranker | DSB-free recombinase plans carry ~zero translocation risk by construction; the guide-QC ranker is validated by a **synthetic positive-control unit test** (hand-constructed guides each tripping one failure mode rank below a clean control) - this tests the ranking logic, not real guide outcomes |

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
  writability is tested for whether it ranks held-out safe harbours above matched-context controls. On a
  gold set **scaled from 5 to 16 independent loci** (8 functionally validated + 8 computationally-defined
  universal-GSH, classic harbours + Lin et al. 2024) this is a **weak signal, honestly bounded**: all-loci
  **AUROC 0.68 (95% CI 0.53-0.82)**, validated-only **0.70 (95% CI 0.48-0.91, underpowered at N=8)** vs a
  safety-only baseline 0.51. The earlier 0.92-on-5 was an over-estimate from tiny N; the AUROC is always
  cited with its CI and N. Writer-family recovery@1 = **0.86** vs prevalence 0.29 across 4 families (14 documented writes, including
  honest misses where labs chose a non-minimal-capacity writer - see Limitations). The earlier "recovery@10 = 1.00, McNemar p" for *targeted* intents was definitional,
  not predictive (an on-target identity term dominates), so it is reported only as a specification-compliance
  table - see `docs/benchmark_circularity.md`. A tool-using agent never fabricates a number.
- **Paper 4 (Bridge off-target engine):** to our knowledge the first measured-data-validated tool that
  **nominates and ranks candidate off-target *locations*** for bridge recombinases. On the measured Perry
  2025 data (6,856 real off-targets) the per-position profile confirms the central core (positions 7-9) is
  the specificity determinant, and the model ranks real off-targets above core-disrupted decoys at AUROC
  0.77 vs 0.62 for Hamming. Stated plainly: it is a **screening tool, not a quantitative safety
  calculator**, it does not quantify how much recombination occurs at each site (sequence-risk vs measured
  magnitude, rho approximately 0.30). A first-of-its-kind beachhead for a genuinely unoccupied gap, not a
  Nature-tier breakthrough; the Writable Genome (Paper 1) remains the flagship novelty.

## The Genome-Writing Bench (v0.2, M2)

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
| **grounded LLM agent** (PEN-Agent) | = planner (grounded) | **PASS** | a real LLM drives the tools; reaches the planner only by grounding every value, 0 fabricated |

**Ungrounded-LLM contrast (T7) - the benchmark separates agents, not just "did it call the tool":** the
*same* models with **no tools** fabricate tool-only values. Under a naive prompt, qwen2.5:7b and Nemotron
both fabricate **100%** of planning fields (and invent in-human clinical numbers no tool could produce -
qwen 100%, Nemotron 67% on ungroundable goals). Even *coached* to refuse, qwen still slips (4%) while
Nemotron refuses fully - but the **grounded agent is 0.0 under every prompt and model, by construction**.
Grounding, not prompting, is what removes fabrication. (Transcripts cached under `data/llm_bench_cache/` for
offline replay; `bench/run.py --ungrounded-live` repopulates them on the VM.)

Per-task (planner vs naive): site selection **0.70** vs 0.51 (validated GSH, N=8; all-16-loci 0.68, CI
0.53-0.82), writer recovery **0.86** vs 0.29 (N=14 writes), off-target **0.77** vs 0.62, intent 7/7,
no-fabrication **PASS** (a hard gate). The gold sets were scaled in v3.1.1 and every metric is reported with
its N and CI - see Limitations. **PEN-Agent** (`pen_stack.agent`) is a
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
│   │   ├── uncertainty.py            v3.2 conformal intervals/sets over the heads (no retraining)
│   │   ├── ood.py                    v3.2 out-of-distribution / extrapolation detector
│   │   ├── structure3d.py            3D structural-risk axis (AlphaGenome contact-map deltas, 11 hijack loci)
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
│   │                                   + v3.2 target_site (hard PAM/att/core reject) / delivery_constraints
│   ├── bridge/                       bridge off-target engine (Paper 4): offtarget / fold_qc / guide_qc / pipeline / cli
│   │                                   + v3.2 offtarget_energetics (position x substitution; held-out 0.88, ships)
│   ├── agent/                        agentic platform: tools / orchestrator / pen_agent / mcp_server / guardrails
│   │                                   + v3.2 epistemic (3-tier status) / scope (known-unknowns matcher)
│   ├── adapt/                        local recalibration / private-data adaptation behind a gate (v3.1, WS-F)
│   ├── env/                          v3.2 optional Gymnasium interface (genome_writing_env; [env] extra)
│   ├── monitor/                      PEN-MONITOR living database (Europe PMC)
│   ├── rag/                          grounded, cited Q&A (hybrid LLM: Ollama primary, Nemotron fallback)
│   ├── validate/                     benchmarks: blind_gsh_discovery / durability_baselines / writer_recovery /
│   │                                   within_locus_ranking / agent_eval / ungrounded_baseline (T7) / adapt_demo /
│   │                                   v3.2 selective_prediction / uncertainty_eval / bench_trust_tasks (T8-T11) /
│   │                                   out_of_scope_refusal / target_site_controls / offtarget_energetics_eval
│   ├── data/                         ingestion (genome, chromatin, integration, TRIP, safety annotations)
│   ├── server/api.py                 FastAPI REST (atlas, crosslink, writable, plan, bridge, ask)
│   ├── ui/app.py                     Streamlit web app (16 pages; v3.2 PEN-Agent shows confidence + epistemic status)
│   └── cli.py                        unified CLI
├── benchmarks/genome_writing_bench/  Genome-Writing Bench v0.2 (T1-T11; tasks / harness / solvers / LEADERBOARD / SHAs)
├── bench/run.py                      one-command bench entrypoint (--agent, --verify)
├── scripts/                          reproducible pipeline drivers (p1_*, p2_*, p4_*, ws_*_report)
├── configs/                          pinned datasets + thresholds + curation (YAML); v3.2: known_unknowns /
│                                       target_sites / delivery_constraints
├── prereg/                           SHA-locked success criteria (paper1..4 + ws_a..ws_h + v3.2 ws_{uq,ep,mc,ba} + locks)
├── data/curated/                     small committed tables (universe, gene coords, measured bridge profile,
│                                       v3.2 bridge_offtarget_energetics.json)
├── data/llm_bench_cache/             28 cached ungrounded-LLM transcripts (T7, offline/CI replay)
├── data/alphagenome_cache/           cached AlphaGenome predictions (tracks + contact maps; offline reproducibility)
├── tests/unit/                       unit + regression + blind-validation suite
├── docs/                             mkdocs site (cards, tutorials, INFRA, DEPLOY, MCP);
│                                       v3.2: uncertainty.md / scope.md / mechanistic_constraints.md / BACKLOG.md
├── docker/                           CUDA image + UI image + pinned requirements
├── tools/penctl.py                   laptop<->VM orchestrator (paramiko SSH/SFTP, Docker-only)
├── docker-compose.yml                one-command self-hostable platform
└── pyproject.toml  CITATION.cff  CHANGELOG.md  LICENSE
```

> **Data policy.** Large artifacts (3 M-row atlases, BigWig tracks, models) and any third-party copyrighted
> data are *not* committed - they are released via Zenodo (DOI) or fetched from the original source, and are
> reproducible by re-running the scripts. Only small curated tables and derived products live in git.

## Installation and quick start

**From PyPI** (the library, CLI, agent, and pure-logic tools):

```bash
pip install pen-stack            # core
pip install "pen-stack[models,bio,bridge,server,services]"   # full stack
```

The wheel ships the importable package and the command-line tools. The **full data pipeline** (the 3 M-row
atlases, BigWig tracks, and curated configs) is distributed via the cloned repo + Zenodo, per the data
policy below; point an installed copy at a checkout with `export PEN_STACK_HOME=/path/to/pen-stack` to use
the config-driven features. Most users who want the whole pipeline clone the repo:

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
- **Every estimate carries its N and CI; statistical power is a stated limitation.** The validated gold
  sets are small: blind GSH discovery rests on 8 functionally-validated harbours (16 curated loci; +35 Pellenz-2019
  exploratory candidates reported separately, near chance), writer recovery on 14 documented writes, within-locus on 5 loci, the
  3D structural sanity on 11 hijacking loci, and the LLM-agent bench on a few goals. Headline AUROCs are
  bootstrap-CI'd and the CIs are wide - e.g. blind GSH discovery is **0.68 (95% CI 0.53-0.82)**, not a
  precise 0.92. Scaling these gold sets (the literature has dozens of candidate harbours and many documented
  large-cargo integrase/CAST/PASTE writes) is the top priority for turning this from a proof of concept into
  an adopted resource; v3.1.1 began that scaling (5 -> 16 GSH loci).
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
  version = {3.2.0},
  url     = {https://github.com/ahmedanees-m/pen-stack}
}
```

**Author:** Anees Ahmed Mahaboob Ali, VIT University, Vellore. MIT licensed.

*Decision-support, not a clinical directive - every score is traceable to public data and a pre-registered
model.*
