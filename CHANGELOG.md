# Changelog

All notable changes to PEN-STACK are documented here. This file follows
[Keep a Changelog](https://keepachangelog.com/) and the program's phase structure.

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
