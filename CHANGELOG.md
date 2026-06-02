# Changelog

All notable changes to PEN-STACK are documented here. This file follows
[Keep a Changelog](https://keepachangelog.com/) and the program's phase structure.

## [3.0.0a3] — 2026-06-02 — Phase 2 (Writer Atlas + Unified Stack → Paper 2)

The broad, cross-family Writer Atlas, the writer↔locus cross-link, and the installable platform.

### Added
- **Writer Atlas** (`pen_stack/atlas/expand.py`, `atlas.parquet`): **33,370 systems across 8 families**
  (31,885 IS110/IS1111 orthologs + curated cores/reps), every row confidence-tagged + ≥1 source DOI,
  targeting metadata inherited from the WT-KB. `configs/atlas_families.yaml` drives the UniProt queries.
- **Mechanism at scale** (`pen_stack/mech/`): ported audited 18-family Pfam whitelist v1.2.1; composite
  co-occurrence rules; **core agreement 1.00** vs audited labels; conflicting calls → review queue.
- **Therapeutic readiness** (`pen_stack/score/therapeutic.py`): deliverability/cargo/human-cell axes,
  components retained (ISCro4 326aa→AAV).
- **Cross-link** (`pen_stack/atlas/crosslink.py`): bidirectional writer↔locus queries; AAVS1 held-out
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
- **Phase 2 COMPLETE** — pre-registered criteria met (`prereg/paper2.yaml` + `SHA256_LOCK_phase2.json`);
  atlas Zenodo DOI pending author upload. Verified on the VM (Docker): API, UI (:8501), RAG with Qwen.

## [3.0.0a0] — 2026-06-01 — Phase 0 (in progress)

Fresh v3.0 monorepo. Supersedes the v1.0 platform repository (archived); consolidates the five prior
repositories (`genome-atlas`, `mech-class`, `pen-score`, `pen-assemble`, `pen-compare`) as provenance.

### Added
- Monorepo scaffold: 13 modules (`atlas`, `mech`, `score`, `wgenome`, `planner`, `bridge`, `monitor`,
  `rag`, `agent`, `ui`, `data`, `validate`, `server`), `pyproject.toml`, Docker image spec, `penctl`
  laptop↔VM orchestrator, CI, `configs/`, `prereg/`.
- `docs/INFRA.md` — three-tier (laptop / VM / Drive) Docker-only, SFTP-only workflow.
- `configs/llm.yaml` — single LLM switch (Ollama + Qwen2.5-7B-Instruct, Apache-2.0).
- `configs/datasets.yaml` — pinned dataset accessions + verified IDs (see VERIFICATION_REPORT_v3.0).

- **WT-KB** (`pen_stack/atlas/`): 8 fully-sourced writer families with reachability tiers; schema enforces the ≥1-DOI sourcing rule.
- **Re-grounded axes** (`pen_stack/score/recalibrate.py`, `configs/score_axes.yaml`): `S_Cargo` from measured bp, `S_Prog` from targeting modality, `length_aa` backfilled — no per-enzyme overrides.
- **Canonical universe** (`pen_stack/atlas/universe.py::assemble`): one path joining the 1,058-entity universe + WT-KB + crosswalk; cross-module consistency test.
- **Descriptive scorecard** (`pen_stack/atlas/scorecard.py`): reframed from the circular certification; blind concordance recovers ISCro4 as the bridge standout without naming it. 21 tests green.

### Notes
- Independent verification of all datasets/IDs/DOIs/tools completed: no critical errors in the v3.0 plan
  (full report in `Final_Part_v3.0/VERIFICATION_REPORT_v3.0.md`).
- **Phase 0 COMPLETE** — all pre-registered success criteria met (`prereg/phase0.yaml` + SHA lock).
