<div align="center">

# PEN-STACK

### A verification and grounding layer for genome-writing AI

Foundation models generate candidate edits; PEN-STACK checks them. It tells you where in the genome a write can be made safely and durably, which enzyme can make it, and how to design the write end to end. Every design is checked against rule-grounded mechanism, returned with calibrated confidence and its provenance, and marked "out of scope" rather than guessed. Numbers come from validated tools, not from a language model.

[![PyPI](https://img.shields.io/pypi/v/pen-stack.svg)](https://pypi.org/project/pen-stack/)
[![CI](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/ci.yml)
[![Publish](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml/badge.svg)](https://github.com/ahmedanees-m/pen-stack/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/ahmedanees-m/pen-stack/branch/main/graph/badge.svg)](https://codecov.io/gh/ahmedanees-m/pen-stack)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/runtime-docker-2496ED.svg)](docker/)

</div>

## Overview

PEN-STACK is an installable Python package and service for the genome-*writing* era, the modality that installs new information into a genome (inserting genes, flipping or excising kilobases, placing programmable landing pads) rather than editing a base in place. Writing is harder and less tooled than editing, and it is gated by questions that have no canonical answer: where can you write, what can write there, and how should the write be designed.

The package consolidates five earlier research projects into one citable stack and adds the maps and the design engine the field was missing: a genome-wide Writable-Genome atlas, a cross-family Writer Atlas, an inverse-design Write Planner, a per-mechanism off-target engine, a design-stage biosecurity gate, immunogenicity and delivery profiling, a calibrated digital twin, and a grounded agent that drives them end to end. All of it runs under one engineered invariant: every reported quantity comes from a validated tool or an out-of-distribution-gated oracle, never from a language model, and anything out of scope is returned as a known-unknown rather than guessed. It runs on a single GPU, uses bulk-downloadable public data, and is validated against pre-registered baselines with the negatives reported in full.

See [docs/](docs/) for the full documentation.

## What it addresses

| Question | The situation today | What PEN-STACK provides |
|---|---|---|
| Where can you write? | Labs re-derive ad-hoc "safe harbour" shortlists from inconsistent criteria; published lists range from thousands of sites to a few dozen, rarely predict expression durability, and usually cover one cell type. | The Writable Genome: a learned, cell-type-aware, writer-aware atlas scoring every locus for safety (genotoxicity risk), durability (whether a cassette stays expressed), and reachability (which enzyme can engage it). |
| What can write there, and how well? | Enzyme capabilities are scattered across papers, with no catalogue placing the genome-writing families on common measured axes with their targeting requirements. | The Writer Atlas: 33,370 enzyme systems across 8 families on common measured axes, joined to the Writable Genome by a bidirectional cross-link. |
| How do I design the write? | Destination, enzyme, cargo, and delivery are interdependent and goal-dependent, and no tool optimises them together. | The Write Planner: inverse design that, given a goal and an edit intent, returns ranked, traceable site, writer, cargo, and delivery plans. |
| Where might the write go off-target? | Off-target behaviour differs by writer mechanism, and most writer classes had no genome-wide screening tool. | A per-mechanism off-target engine across five writer classes (RNA-guided nuclease, serine integrase, prime-editing integrase, CAST, and bridge recombinase). It behaves like established nuclease tools where genome-wide assay data exists and reports a truthful mechanism-based screen, with its validation status, where it does not. |
| Can I trust the outputs? | LLM design assistants produce fluent but unsourced quantities, and large-cargo design is dual-use. | A no-fabrication invariant (every number traces to a validated tool) that we verify with the model live, and a design-stage biosecurity gate that screens function, family, taxon, and raw sequence before any protocol can be emitted. |

## Architecture

A goal enters through one of the interfaces. The agent layer turns it into candidate designs. Every candidate passes through the verifier, the central gate: it runs a biosecurity screen first, checks the design against the rule base, attaches a calibrated confidence and a per-axis immune-risk profile, and discards anything that is unsafe, illegal, or uncalibrated. The reference layers and the oracle mesh supply the grounded answers the verifier and planner rely on, and everything rests on public data. No value is reported without a traceable source, and no value comes from a language model.

```text
                         Interfaces
          CLI    |    REST API    |    MCP server    |    Web app
                                |
                                v
                        Agent layer
       Co-scientist   |   Write Planner   |   Experiment Designer
       (goal -> typed WriteSpec -> ranked site / writer / cargo / delivery plan)
                                |
                                v
   +===========================================================+
   |   VERIFIER  (the central gate, runs on every design)      |
   |   1. biosecurity screen   2. legality rules               |
   |   3. calibrated confidence   4. per-axis immune-risk       |
   |   unsafe / illegal / uncalibrated designs are rejected    |
   +===========================================================+
                                |
                                v
                   Reference and model layers
   +-------------------+  +----------------+  +-------------------+
   | Writable Genome   |  | Writer Atlas   |  | Oracle mesh       |
   | per-locus safety, |  | 33,370 enzyme  |  | ViennaRNA, Evo2,  |
   | durability,       |  | systems, 8     |  | AlphaGenome, ESM3,|
   | expression-       |  | families, on   |  | RFdiffusion,      |
   | robustness,       |  | common axes,   |  | ProteinMPNN live; |
   | reachability,     |  | cross-linked   |  | AF3, Boltz-2 held |
   | per-mechanism     |  | to every locus |  | under one Oracle- |
   | off-target        |  |                |  | Result contract   |
   +-------------------+  +----------------+  +-------------------+
                                |
                                v
   Public data: hg38, ENCODE / Roadmap chromatin, TRIP, CancerMine (CC0),
   DepMap, VISDB, UniProt, Pfam / InterPro, Europe PMC, Perry 2025 bridge data
```

## Components

| Component | Module | What it does |
|---|---|---|
| Writable Genome | `pen_stack.wgenome` | Learned per-locus safety (genotoxicity risk), expression-robustness (durability), and writer reachability; a 3D structural-risk axis; and a per-mechanism off-target engine across five writer classes with per-class validation status. |
| Writer Atlas | `pen_stack.atlas`, `.mech`, `.score` | Cross-family enzyme catalogue and Writer-Targeting knowledge base, cross-linked to loci. |
| Write Planner | `pen_stack.planner` | Inverse design conditioned on an edit intent, including the delivery palette and the delivery-immunology profile. |
| Verifier | `pen_stack.verify`, `pen_stack.rules` | `verify(design)` returns legality, biosecurity verdict, calibrated confidence, and the immune-risk profile as distinct axes. |
| Biosecurity gate | `pen_stack.safety` | A dual-use screening gate that runs first in `verify()`, screening declared function, family, and taxon signatures and translating a raw cargo sequence against curated Pfam toxin-family profiles; a refusal short-circuits scoring, with a tamper-evident audit trail. It reads hazard content only from declared fields (`cargo_function`, `function_annotation`, `goal_function`, `source_taxon`, `organism`, `host_taxon`, `cargo_seq`, `cargo_sequence`); content in `edit_intent` or other framing fields is not screened, so a verdict with `declared_signal=False` means "nothing screenable was declared", not "screened and safe" (see [`docs/biosecurity.md`](docs/biosecurity.md)). |
| Oracle mesh | `pen_stack.oracles` | One `OracleResult` contract over the biomolecular foundation models, with provenance, native uncertainty, and a scope card; generated output is a candidate, out-of-distribution inputs are flagged. |
| World-model graph | `pen_stack.graph` | A typed, provenanced knowledge graph with a gated, propose-only update loop. |
| Generative designer | `pen_stack.design` | Proposes candidate writing systems and keeps only those that pass safety, legality, and calibration, returning a Pareto frontier. |
| Digital twin | `pen_stack.twin` | Calibrated, out-of-distribution-gated outcome prediction, bounded at phenotype. |
| Experiment designer | `pen_stack.active` | Active learning by expected information gain, with a retrospective active-versus-random evaluation. |
| Build interface | `pen_stack.build` | Safety-gated protocol export (draft only, never auto-run) and gated ingestion of results, with a cloud-lab connector that runs the biosecurity gate before any submission. |
| Closed loop | `pen_stack.loop`, `pen_stack.active` | A gated design, build, test, learn loop with drift detection and versioned, reversible recalibration; an SDL-brain benchmark and a validation-campaign engine that orders the most-informative next measurements by expected information gain. |
| Write intent (WriteSpec) | `pen_stack.spec` | A typed, ontology-backed `WriteRequest` (an SBOL3 profile) with a grounded extractor that resolves free text to verified ontology ids, asks clarifying questions on ambiguity, and runs a SAT feasibility check. |
| Agent, co-scientist, and chat | `pen_stack.agent`, `pen_stack.web`, `pen_stack.rag` | Goal to cited, auditable plan; MCP server; the co-scientist that drives the loop; and the grounded conversational chat (four lanes: design, explain, meta, general; provenance-tagged retrieval; a swappable LLM provider). |
| Bridge off-target engine | `pen_stack.bridge` | The measured-data-validated off-target engine for bridge recombinases (IS110/IS621): candidate-site nomination, ranking, and guide QC, validated on the Perry 2025 data. |
| Immunogenicity and delivery | `pen_stack.planner` | Per-writer T-cell immunogenicity profiling (NetMHCpan / NetMHCIIpan) with a human-albumin self-control, a delivery-vehicle palette, and anti-drug-antibody and anti-PEG proxies, each labelled by validation status. |
| Interfaces and manifests | `pen_stack.server`, `pen_stack.web`, `pen_stack.ui`, `pen_stack.cli`, `pen_stack.api` | REST API, web application, and command-line tools, together with the machine-readable capability and scope manifests an external agent routes on (including the known-unknowns registry). |
| Data, adaptation, and monitoring | `pen_stack.data`, `pen_stack.adapt`, `pen_stack.monitor`, `pen_stack.env`, `pen_stack.validate` | Dataset ingestion (ENCODE, TRIP, safety annotation, integration sites); continual adaptation with versioned recalibration; Europe PMC literature polling and triage; the genome-writing environment and policies; and the blind-validation and benchmark-task drivers. |

## Key results

All results are blind and pre-registered (success criteria, baselines, and held-out sets are SHA-locked in [`prereg/`](prereg/) before any model sees the test data). Estimates are reported with their sample size and confidence interval.

- **Expression-robustness axis (the headline result).** A per-locus prediction of whether an integrated cassette stays expressed rather than being positionally silenced. On measured human K562 position-effect data (Leemans 2019) the axis reaches a held-out Spearman rho of 0.571 (0.558 on an independent held-out variant), and it is empirically *distinct* from ePRIDICT's chromatin prediction of prime-editing efficiency (rho 0.212, R-squared 0.041 across 7,295 loci): a complementary signal, not a restatement of one. It is validated at exact-site resolution; the deployment commonly serves coarse 1-kb features, at which the axis reaches rho about 0.16, and that gap is reported as a result rather than claimed away. See [`benchmarks/position_effect_human/`](benchmarks/position_effect_human/).
- **Writable Genome and the integrated safety filter.** A genome-wide atlas of 3,031,030 loci across three cell types (K562, HepG2, CD34+ HSPC) recovers experimentally validated safe harbours as highly writable and clinical genotoxic loci as non-writable, blind. The three-way integrated score (safety x durability x reachability) is characterised as a *reject-known-bad safety filter*: against oncogene-distance and accessibility-matched controls it reaches AUROC 0.679 (95% CI 0.536 to 0.825) versus a safety-only baseline of 0.51, with real false negatives on documented clinical genotoxic loci reported in full; it is not a calibrated genotoxicity predictor.
- **Writer Atlas.** 33,370 enzyme systems across 8 families on common measured axes; the mechanism classifier agrees with the audited labels on the curated core (1.00); the cross-link to loci is validated on AAVS1. Writer-family recovery at rank 1 is 0.86 against a prevalence of 0.29.
- **Per-mechanism off-target engine.** The RNA-guided nuclease path *wraps* the published CRISOT scorer (which beats naive homology, CRISOT's own result, stated plainly). The serine-integrase path, on the Chalberg 115-site human genomic pseudo-attP set, reaches AUROC 0.637 and AUPRC 0.215, beating a palindrome baseline (CI excludes zero) and matching an attP-similarity baseline on AUROC while beating it on AUPRC: an informative two-stage result, reported as such. The bridge path (Perry 2025, 6,856 measured off-targets) ranks real off-targets above core-disrupted decoys at AUROC 0.77 versus 0.62 for Hamming distance. The bridge and CAST paths are mechanism-based screens, not per-site risk calculators, and are labelled as such.
- **No fabrication, measured with the model live.** Given no tools, an ungrounded LLM fabricates 91 to 99 percent of the tool-only planning quantities (writability, safety, durability, off-target count, structural risk, coordinate) under a naive prompt, across three model families spanning a small local model to hosted-frontier models; the same models driving the validated tools as an agent fabricate none, every number audited to a direct tool call. Anti-fabrication prompting is an uneven guardrail; grounding is not. See [`benchmarks/grounding_llm_on/`](benchmarks/grounding_llm_on/) and [`benchmarks/agentic_baseline/`](benchmarks/agentic_baseline/).

## Installation

From PyPI (the library, CLI, agent, and pure-logic tools):

```bash
pip install pen-stack                                          # core
pip install "pen-stack[models,bio,bridge,server,services]"     # full stack
```

The wheel ships the importable package and the command-line tools. The full data pipeline (the multi-million-row atlases, BigWig tracks, and curated configs) is distributed via the cloned repository and Zenodo. Most users who want the whole pipeline clone the repository:

```bash
git clone https://github.com/ahmedanees-m/pen-stack.git && cd pen-stack
pip install -e ".[dev]"                                        # core and tests
pip install -e ".[models,bio,bridge,server,services]"          # full stack
pytest -q
pen-stack info                                                 # stack status
python bench/run.py --agent                                    # run the Genome-Writing Bench
```

`pen-stack` and its dependencies install from wheels on Linux, macOS, and Windows (Python >= 3.11). One
system library is not pip-installable: LightGBM needs the OpenMP runtime, which standard Linux, conda, and
macOS environments (and the CI image) already provide. On a minimal Debian base image only, install it once
with `apt-get install -y libgomp1`.

A committed **1-chromosome demo atlas** (`data/demo/atlas_k562.parquet`, chr19) lets a fresh clone run the
safe-harbour quickstart immediately - chr19 carries the canonical AAVS1 safe harbour. Point `PEN_ATLAS_DIR`
at it, or fetch the full genome-wide release from Zenodo:

```bash
PEN_ATLAS_DIR=data/demo pen-stack writable --gene AAVS1 --ct k562   # runs on the committed chr19 demo
ZENODO_DOI=<deposit DOI> bash scripts/fetch_artifacts.sh           # full atlas -> data/out/ (all cell types)
```

## Quick start

Query the stack from the command line:

```bash
pen-stack info                                                 # stack status
pen-stack atlas --coverage                                     # Writer Atlas coverage (33,370 systems, 8 families)
pen-bridge design --target ACGTGTCTACGTGA --donor TTGCATCTAGGCAC
```

The locus queries read a writability atlas. A fresh clone already ships the 1-chromosome demo atlas (chr19),
which covers the canonical AAVS1 safe harbour:

```bash
export PEN_ATLAS_DIR=data/demo                                 # committed chr19 demo atlas
pen-stack writable --gene AAVS1 --ct k562                      # rank writable loci near a gene
pen-stack crosslink --chrom chr19 --bin 55117                  # which writers reach that locus
pen-stack plan --gene AAVS1 --intent knock_in_with_disruption --cargo-bp 2000
```

Genome-wide queries (any gene, all cell types) need the full atlas from the Zenodo deposit:

```bash
ZENODO_DOI=<deposit DOI> bash scripts/fetch_artifacts.sh       # installs data/out/ + models/
pen-stack writable --gene CCR5 --ct k562
```

Self-host the platform (API, UI, agent, MCP, and the local model):

```bash
docker compose up -d api ui mcp ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct     # first run only (local fallback model)
# UI on :8501, API on :8000, MCP on :8765 (see docs/DEPLOY.md)
```

The React web platform is an alternative single-origin front end that serves the API on the same port, so it is started on its own rather than alongside `api`:

```bash
docker compose up web ollama                                   # web platform on :8000
```

The LLM backend is optional and non-load-bearing: it narrates and routes, but every number and citation comes from a validated tool, so the core scientific compute runs with no language model at all. See [docs/DEPLOY.md](docs/DEPLOY.md).

## Benchmarks

The Genome-Writing Bench is a one-command, SHA-locked benchmark for the writing side of genome engineering: where to write, what writer to use, how to design the cargo, and what off-target or structural risk a write carries. Each task has a deterministic scorer and a documented ground-truth source, and no task is scored against a circular label.

```bash
python bench/run.py --agent
docker compose run --rm bench python bench/run.py --agent       # on the clean image
```

The deterministic planner beats the naive baselines on the grounded tasks; a tool-using LLM agent reaches the planner's numbers only by grounding every value (zero fabricated), while the same models with no tools fabricate the tool-only fields. See [`benchmarks/genome_writing_bench/`](benchmarks/genome_writing_bench/). The held-out public leaderboard is the [Genome-Writing Challenge](benchmarks/genome_writing_challenge/).

Benchmarks are SHA-locked, and most ship a harness, a frozen split, and a committed `metrics.json`; the two open leaderboards ship tasks and a submission protocol instead. A fresh clone reproduces the central numbers with no download and no API key:

```bash
make repro        # demo-atlas quickstart, grounding eval, agentic baseline, and the recomputed headline result
make repro-human  # recompute the headline human K562 expression-robustness result (rho=0.571) from source data
make repro-full   # the above plus the genome-wide atlas benchmarks (needs 'make fetch' with ZENODO_DOI)
```

`make repro` also re-hashes every SHA-locked pre-registration against the committed bytes (`scripts/prereg_manifest.py`, which emits the full manifest `prereg/PREREG_MANIFEST.md`) and asserts it in continuous integration, so a live lock cannot silently drift from the file it fixes. The ten claims in the honesty ledger each cite a committed pre-registration verifiable from a bare clone with `sha256sum prereg/<file>`; the full eighty-lock manifest is in `prereg/PREREG_MANIFEST.md`.

The headline expression-robustness result is **recomputed from source, not read from a stored number**:
`scripts/p2_build_human_head.py` (run by `make repro-human`, and folded into `make repro`) trains the shipped
twin on the committed Leemans K562 features table, holds out chromosomes 3/8/12 exactly as the sealed
pre-registration specifies, and asserts the recomputed held-out Spearman correlation (0.5711) matches the
committed metrics. The three headline analyses each ship their metrics: the human K562 expression-robustness
head ([`benchmarks/position_effect_human/`](benchmarks/position_effect_human/)), the integrase off-target set
([`benchmarks/offtarget/integrase_chalberg/`](benchmarks/offtarget/integrase_chalberg/)), and the clinical
genotoxicity panel ([`benchmarks/genotox_panel/`](benchmarks/genotox_panel/)).

## Built on prior repositories

PEN-STACK consolidates and re-grounds five earlier projects. Their reusable assets are imported here; the originals are archived read-only for provenance and DOI stability.

| Repository | Pinned version | What is reused | What changed |
|---|---|---|---|
| [genome-atlas](https://github.com/ahmedanees-m/genome-atlas) | v0.7.2 | The audited 18-family Pfam backbone behind the knowledge base and the at-scale mechanism classifier. | The GraphSAGE link-prediction framing was retired. |
| [mech-class](https://github.com/ahmedanees-m/mech-class) | v0.5.4 | The mechanism classifier (Pfam, RHEA, CRISPRcasdb, UniProt). | Reused as the family and mechanism caller. |
| [pen-score](https://github.com/ahmedanees-m/pen-score) | v0.1.3 | The scoring axes (delivery, immunogenicity, cargo, and others). | The cargo and programmability axes were re-grounded; hand-set overrides removed. |
| [pen-assemble](https://github.com/ahmedanees-m/pen-assemble) | v0.5.2 | The ortholog sequence set. | De-novo chimera generation was replaced by DMS-grounded point-variant proposal. |
| [pen-compare](https://github.com/ahmedanees-m/pen-compare) | v0.1.0 | The 1,058-entity universe, scorecard scaffold, and tests. | The circular five-gate certification became a descriptive scorecard with blind concordance. |

A single assembly path (`pen_stack/atlas/universe.py`) feeds the classifier, the scorer, and the scorecard the same metadata, so cross-module inconsistencies cannot recur.

## Repository structure

```
pen-stack/
  README.md  LICENSE  CITATION.cff                  project front matter (MIT; cite-this-repository)
  pyproject.toml  MANIFEST.in                       packaging and sdist contents
  DATA_SOURCES.md  DATA_LICENSES.md                 data provenance index and the open-data licensing policy
  pen_stack/            the installable package
    spec/               WriteSpec: typed SBOL3-profile intent layer, grounded extractor, ontology resolvers, SAT feasibility
    wgenome/            Writable Genome: features, safety, durability, writability, uncertainty, structure3d, off-target nomination
    atlas/              Writer Atlas, knowledge base, cross-link, variant proposal, canonical universe, writer-efficiency predictor
    mech/  score/       mechanism classification at scale; re-grounded therapeutic-readiness axes
    planner/            Write Planner: optimisation, cargo, routing, delivery palette, delivery immunology, capsid fitness
    bridge/             bridge off-target engine and guide QC
    oracles/            oracle mesh: the OracleResult contract and adapters over the foundation models, with binding-affinity and per-oracle reliability
    graph/              living world-model knowledge graph (gated, propose-only)
    rules/  verify/     machine-readable rule base, the verify(design) service, and the proof-object with repair hints
    safety/             the biosecurity and dual-use gate, with standards concordance
    design/  twin/      generative designer; calibrated digital twin with a learned position-effect model
    active/  build/     experiment designer with the SDL-brain benchmark and validation-campaign engine; safety-gated build interface and cloud-lab connector
    loop/               the gated design-build-test-learn loop
    rag/                provenance-tagged retrieval corpus, embedder, and four-branch ground router (social, cited, general, abstained)
    agent/              agent platform, co-scientist, MCP server
    data/               dataset ingestion (ENCODE, TRIP, safety annotation, integration sites)
    adapt/              continual adaptation: ingest, fine-tune, versioned recalibration, report
    validate/           blind-validation and benchmark-task drivers (safe-harbour discovery, outcome calibration, adversarial / co-scientist / graph / rule / trust task suites)
    monitor/            Europe PMC literature polling and triage
    env/                the genome-writing environment and policies
    api/  web/  server/ ui/  cli.py    capability and scope manifests, web platform with the grounded chat and swappable LLM provider, REST API, CLI
  benchmarks/           SHA-locked benchmarks; most carry a harness, a frozen split, and a committed metrics file:
    genome_writing_bench/  genome_writing_challenge/     the bench and the public held-out leaderboard (tasks + submission protocol)
    position_effect/  position_effect_human/             expression-robustness axis; human K562 external validation (rho=0.571)
    offtarget/  genotox_panel/                            per-mechanism off-target; clinical insertional-oncogenesis panel
    grounding_llm_on/  agentic_baseline/                  model-live no-fabrication eval; tool-driving agentic baseline
    chat_grounding/  chat_safety/  chat_routing/  chat_headtohead/   grounded-chat probe sets
    verify/  writespec/  delivery/  immuno/  loop/  oracle/  writer_efficiency/  priorart/   per-stage benchmarks and prior-art positioning
  scripts/              reproducible pipeline drivers (fetch_artifacts.sh installs the Zenodo release; prereg_manifest.py re-hashes every lock)
  bench/                the benchmark runner (bench/run.py; also the compose `bench` service)
  tools/                developer command-line helper (penctl.py)
  examples/             worked integration examples (external agent, MCP client, agent tool specs)
  schemas/              JSON schema for the typed WriteSpec intent layer
  Makefile              one-command reproduction (make fetch, make repro, make repro-human, make repro-full)
  configs/              pinned datasets, thresholds, curation, and the provider-agnostic LLM switch (YAML, plus reference FASTA)
  prereg/               SHA-locked pre-registered success criteria, and the generated PREREG_MANIFEST.md
  data/
    curated/            small committed tables (gene_coords, ...)
    demo/               committed 1-chromosome demo atlas (chr19) for clean-clone reproduction
    llm_bench_cache/    committed model-live transcripts for the grounding eval (replay offline, no key needed)
    priorart/  offtarget/  alphagenome_cache/             committed derived products backing the sealed benchmarks
  tests/                unit and regression suite (tests/unit); the blind-validation drivers live in pen_stack/validate/
  docs/                 documentation site (tutorials, method cards, deployment); mkdocs.yml at the root
  docker/               container images and pinned requirements
  model_servers/        self-hosted model-server images (ProteinMPNN, ESM3, RFdiffusion)
  oracle_cache/         committed oracle responses so cached oracle paths replay offline
  web/                  React single-page frontend for the web platform
  Dockerfile            reproducible image (make repro / pytest entrypoints)
  docker-compose.yml    self-hostable platform (api, ui, mcp, ollama, and the alternative single-origin web front end)
  docker-compose.models.yml   the self-hosted model servers
  .github/workflows/    continuous integration (test matrix, data-licence gate) and the PyPI publish workflow
```

Large artifacts (multi-million-row atlases, BigWig tracks, trained models) and any third-party copyrighted data are not committed. They are released via Zenodo or fetched from the original source with `scripts/fetch_artifacts.sh`, and are reproducible by re-running the pipeline. Only small curated tables, the demo atlas, committed benchmark metrics, and derived products live in git, so a fresh clone can run the quickstart and replay every benchmark offline.

## Data sources

All public, and license-clean by policy. Genome and annotation: hg38 (UCSC), GENCODE v46. Chromatin: ENCODE and Roadmap (ATAC/DNase and histone marks for K562, HepG2, CD34+ progenitor, and mouse ES-Bruce4). Position-effect: TRIP (Akhtar 2013, GEO GSE49806/GSE49807) and the Leemans 2019 K562 TRIP data, which is the external validation of the expression-robustness axis. Safety: **CancerMine (CC0)** is the default oncogene and tumour-suppressor source; DepMap Public 26Q1 essentiality; LaFave 2014 MLV integrations; VISDB. Enzymes: UniProt orthologs, Pfam and InterPro. Off-target: the Perry 2025 bridge-recombinase off-target and DMS data (copyrighted, kept local, only derived products released) and the Chalberg 2006 genomic pseudo-attP set. Literature and reagents: Europe PMC, Addgene.

License-restricted sources (COSMIC Cancer Gene Census, OncoKB) are **never committed and never used as training data**; they are optional, local-only enrichers a registered user pulls under their own license, and a CI test fails if a restricted source appears as a shipped derived-data source. Every accession and DOI is pinned in [`configs/datasets.yaml`](configs/datasets.yaml) and indexed in [`DATA_SOURCES.md`](DATA_SOURCES.md); the full open-data policy is in [`DATA_LICENSES.md`](DATA_LICENSES.md).

## Validation approach

- Pre-register before training: success criteria, baselines, and held-out sets are SHA-locked in `prereg/` before any model sees the test data.
- Always report a baseline: a safety-only far-from-oncogene prior and CancerMine oncogene distance for the integrated score; a learned lamina-associated-domain chromatin baseline and ePRIDICT for the expression-robustness axis; intent-blind ranking for the planner; and attP-similarity, palindrome, or Hamming-distance baselines for the per-mechanism off-target paths.
- Guard against circularity: the expression-robustness axis is validated with lamina and heterochromatin features removed, so it cannot restate a chromatin baseline, and no task is scored against a label derived from the model's own features (asserted by a dedicated de-circularization test).
- Blind external concordance: recover validated safe harbours, clinical genotoxic loci, documented writes, and measured off-targets the model never trained on.
- Report failure: cross-cell-type degradation, the exact-site-versus-served-resolution gap, small benchmark sizes, and the limits of sequence-only off-target magnitude prediction are reported as results, not footnotes.
- Every estimate carries its sample size and confidence interval. The validated gold sets are small, and statistical power is a stated limitation; scaling them is the top priority for turning the proof of concept into an adopted resource.
- Grounded services: every quantitative answer comes from a validated tool call, never a language model, verified with the model live; the living database never auto-edits the atlas; clinical directives are refused.

## License and attribution

MIT licensed. Developed at Vellore Institute of Technology, Vellore. Authors and ORCIDs are listed in
[CITATION.cff](CITATION.cff).

## API stability

0.1.0 is the first public release. It establishes the committed public API: the SDK functions, the 44 REST
endpoints, the 16 MCP tools, and the 20-entry capability manifest. These follow semantic versioning, with a
one-minor-version deprecation warning before any breaking change. Stable surfaces carry calibrated uncertainty and an explicit
validation status. The mechanism-based off-target paths (serine-integrase, bridge, and CAST) are marked
experimental and may change as measured data becomes available.

Decision-support, not a clinical directive. Every score is traceable to public data and a pre-registered model.
