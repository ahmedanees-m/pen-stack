# Changelog

All notable changes to PEN-STACK are documented here. This file follows
[Keep a Changelog](https://keepachangelog.com/) and the program's phase structure.

## [Unreleased] - 2026-06-03 - honest reframing, repository polish, coverage

### Changed
- **Paper 4 reframed to its honest scope.** `pen-bridge` is positioned as the first measured-data-validated
  tool that **nominates and ranks candidate off-target *locations*** for bridge recombinases - a
  **screening tool, not a quantitative safety calculator**. The AUROC 0.77 vs 0.62 result is stated with
  its caveat (favourable negative set; mostly tests core integrity), and the magnitude limitation
  (sequence-risk does not rank recombination amount, rho ~0.30) is named as the single most important
  limitation. Application-Note tier, first-of-its-kind for an unoccupied gap; the Writable Genome remains
  the flagship. Manuscript + `prereg/paper4.yaml` + summaries updated.
- **Variant-effect reframed:** the DMS recovers KNOWN enhancers (a catalogue feature), it is not a novel
  variant-design method; EVOLVEpro is the engine to wrap when generating new variants.
- **Repository made clean ASCII:** removed all decorative emojis and em/en dashes and other non-ASCII
  punctuation across code, docs, configs, and manuscripts (box-drawing tree characters kept).

### Added
- 72-system ortholog characterisation (`bridge/ortholog_screen.py`) - explicitly DESCRIPTIVE (Table S1 has
  no activity label): sequence-similarity organisation vs the validated standout ISCro4 (IS621 ranks most
  similar, a sanity check). Exploratory secondary result, N ~72.
- Coverage: CI runs `pytest --cov`, uploads to Codecov, and publishes a self-hosted coverage badge
  (`tools/make_coverage_badge.py` -> `.github/badges/coverage.svg`). Unit-test coverage of the core logic
  is **69%** (integration-only modules that need GPU/VM/network/LLM are excluded via `[tool.coverage.run]`).
- Professional, emoji-free README with connected-repo badges (genome-atlas / mech-class / pen-score /
  pen-assemble / pen-compare), an architecture diagram, and the problem/gaps explanation.

## [3.0.0a5] - 2026-06-02 - Phase 1.5 (Bridge-recombinase off-target engine -> Paper 4, BEACHHEAD)

The first public instrument: a bridge-recombinase off-target screening tool.

### Added
- **Off-target engine** (`pen_stack/bridge/offtarget.py` + `configs/bridge_offtarget_profile.yaml`):
  genome-wide hg38 pseudosite scan (CT-core seed, per-chromosome, memory-bounded) + a position-weight
  risk model grounded in the published mechanism. **Beats naive Hamming: AUROC 1.00 vs 0.59** at
  separating core-preserving (real-risk) from core-disrupting (abolished) sites. Exposes
  `predict_offtargets(family, site)` - completes the Phase-3 Planner cargo hook.
- **Fold / cross-loop QC** (`bridge/fold_qc.py`): ViennaRNA fold (verified MFE on a 190-nt design) +
  TBL/DBL cross-loop complementarity.
- **Activity framework** (`bridge/activity.py`): exploratory DMS + 72-system trainer (deferred; data paywalled).
- **`pen-bridge`** (`bridge/pipeline.py`, `bridge/cli.py`, `/bridge/design` API): **wraps** the Arc
  BridgeRNADesigner (verified) and adds the off-target + QC layer.
- `validate/paper4_validation.py` + `scripts/p4_genome_scan.py`; `prereg/paper4.yaml` + SHA lock.

### Notes
- **Phase 1.5 COMPLETE** - pre-registered criteria met (or honestly gated): the off-target engine,
  ViennaRNA fold, and designer wrap are verified on the VM (real hg38 scan: chr22 in ~21 s). The *blind
  recall of Perry 2025's measured off-targets* and the DMS/activity model are gated on the paywalled
  Perry 2025 supplementary (drop in via `ingest.load_offtarget_profile`). Completes the deferred Phase-2
  Section 2.4 and Phase-3 Section 3.2 hooks. 68 tests green; ruff clean. **All program phases (0,1,1.5,2,3) now done.**

## [3.0.0a4] - 2026-06-02 - Phase 3 (The Write Planner + agentic platform -> Paper 3, CAPSTONE)

Inverse design + the paper-defining recovery@k benchmark + the agentic platform.

### Added
- **Inverse-design optimiser** (`pen_stack/planner/optimize.py`, `configs/intent_weights.yaml`): an
  `edit_intent`-conditioned objective whose `target_gene_sign` flips whether hitting the target gene is
  penalised or rewarded - the same TRAC site ranks #1 (knock-in) vs #101 (safe-harbour).
- **Cargo/delivery** (`planner/cargo.py`, `planner/delivery.py`): donor spec + size check + delivery rule
  table; bridge/seek off-target via an optional Phase-1.5 hook (pending until 1.5).
- **End-to-end Planner** (`planner/pipeline.py`, `report.py`, `/plan` API, `pen-stack plan` CLI): ranked,
  fully traceable plans with per-field provenance.
- **Two-stratum recovery@k benchmark** (`validate/paper3_benchmark.py`, `data/benchmark_panel.csv`,
  `prereg/paper3.yaml`): **discriminating stratum planner 1.00 vs baseline 0.00, McNemar p=0.0156, gap CI
  [1.0,1.0] excludes zero; control tie 0.67=0.67**. Panel cited to Europe-PMC-verified sources.
- **Forward hypotheses** (`validate/forward_hypotheses.py`): date-stamped novel F8/SERPINA1/CISH/HBA1
  proposals + grounded cited ranking.
- **Agentic platform**: `agent/tools.py` + `agent/orchestrator.py` (Ollama tool-calling, auditable trace,
  no-fabrication, refusals), `agent/mcp_server.py` (fastmcp), `docker-compose.yml` + `docker/ui.Dockerfile`
  + Streamlit **Agent** page + `docs/DEPLOY.md`/`docs/MCP.md`, `validate/agent_eval.py`.
- Shipped `data/curated/gene_coords.parquet` (GENCODE-derived) so tools work in any container.

### Notes
- **Phase 3 COMPLETE** - pre-registered criteria met (`prereg/paper3.yaml` + `SHA256_LOCK_phase3.json`).
  Agent verified on the VM in LLM mode (no-fabrication + plan-equivalence + refusals all pass). 63 tests
  green; ruff clean. Wet-lab (3.7) skipped - non-gating. Bridge off-target hook completes with Phase 1.5.

## [3.0.0a3] - 2026-06-02 - Phase 2 (Writer Atlas + Unified Stack -> Paper 2)

The broad, cross-family Writer Atlas, the writer<->locus cross-link, and the installable platform.

### Added
- **Writer Atlas** (`pen_stack/atlas/expand.py`, `atlas.parquet`): **33,370 systems across 8 families**
  (31,885 IS110/IS1111 orthologs + curated cores/reps), every row confidence-tagged + >=1 source DOI,
  targeting metadata inherited from the WT-KB. `configs/atlas_families.yaml` drives the UniProt queries.
- **Mechanism at scale** (`pen_stack/mech/`): ported audited 18-family Pfam whitelist v1.2.1; composite
  co-occurrence rules; **core agreement 1.00** vs audited labels; conflicting calls -> review queue.
- **Therapeutic readiness** (`pen_stack/score/therapeutic.py`): deliverability/cargo/human-cell axes,
  components retained (ISCro4 326aa->AAV).
- **Cross-link** (`pen_stack/atlas/crosslink.py`): bidirectional writer<->locus queries; AAVS1 held-out
  check passes (0.90 writability + bridge-reachable). Per-family caches for k562/hepg2/hspc.
- **Variant proposal** (`pen_stack/atlas/variant_propose.py`): point-mutation framework + retrospective
  harness, no chimeras; DMS model pluggable (Phase 1.5).
- **PEN-MONITOR** (`pen_stack/monitor/`): Europe PMC living-database engine; back-test surfaces ISPpu10;
  never auto-edits the atlas; every candidate cited.
- **Grounded RAG** (`pen_stack/rag/`, `pen_stack/agent/guardrails.py`): numbers from tool calls, claims
  cited, clinical directives refused; optional Ollama/Qwen phrasing layer (presentation only).
- **Stack**: unified CLI subcommands, FastAPI server (`pen_stack/server/api.py`), Streamlit platform UI
  (Writer Atlas + Ask pages), mkdocs site + 4 use-case tutorials. 46 tests green; ruff clean.

### Notes
- **Phase 2 COMPLETE** - pre-registered criteria met (`prereg/paper2.yaml` + `SHA256_LOCK_phase2.json`);
  atlas Zenodo DOI pending author upload. Verified on the VM (Docker): API, UI (:8501), RAG with Qwen.

## [3.0.0a0] - 2026-06-01 - Phase 0 (in progress)

Fresh v3.0 monorepo. Supersedes the v1.0 platform repository (archived); consolidates the five prior
repositories (`genome-atlas`, `mech-class`, `pen-score`, `pen-assemble`, `pen-compare`) as provenance.

### Added
- Monorepo scaffold: 13 modules (`atlas`, `mech`, `score`, `wgenome`, `planner`, `bridge`, `monitor`,
  `rag`, `agent`, `ui`, `data`, `validate`, `server`), `pyproject.toml`, Docker image spec, `penctl`
  laptop<->VM orchestrator, CI, `configs/`, `prereg/`.
- `docs/INFRA.md` - three-tier (laptop / VM / Drive) Docker-only, SFTP-only workflow.
- `configs/llm.yaml` - single LLM switch (Ollama + Qwen2.5-7B-Instruct, Apache-2.0).
- `configs/datasets.yaml` - pinned dataset accessions + verified IDs (see VERIFICATION_REPORT_v3.0).

- **WT-KB** (`pen_stack/atlas/`): 8 fully-sourced writer families with reachability tiers; schema enforces the >=1-DOI sourcing rule.
- **Re-grounded axes** (`pen_stack/score/recalibrate.py`, `configs/score_axes.yaml`): `S_Cargo` from measured bp, `S_Prog` from targeting modality, `length_aa` backfilled - no per-enzyme overrides.
- **Canonical universe** (`pen_stack/atlas/universe.py::assemble`): one path joining the 1,058-entity universe + WT-KB + crosswalk; cross-module consistency test.
- **Descriptive scorecard** (`pen_stack/atlas/scorecard.py`): reframed from the circular certification; blind concordance recovers ISCro4 as the bridge standout without naming it. 21 tests green.

### Notes
- Independent verification of all datasets/IDs/DOIs/tools completed: no critical errors in the v3.0 plan
  (full report in `Final_Part_v3.0/VERIFICATION_REPORT_v3.0.md`).
- **Phase 0 COMPLETE** - all pre-registered success criteria met (`prereg/phase0.yaml` + SHA lock).
