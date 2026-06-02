# Reproducibility — Paper 1 (The Writable Genome)

**Phase 1, Step 1.13.** Every released artifact is regenerable from public data by re-running the pipeline.

## Environment
- One Docker image on a single GPU VM (24 CPU / 16 GB GPU). Build: `penctl build` →
  `docker/Dockerfile.phase1` (CUDA base + LightGBM/torch + pyBigWig/pybedtools/biopython/pyliftover).
- Laptop runs only `tools/penctl.py` (paramiko SSH/SFTP); all heavy steps are `docker run` on the VM.
- Pinned deps: `docker/requirements.txt`; pinned datasets/accessions: `configs/datasets.yaml`.

## Pre-registration
`prereg/paper1.yaml` (success criteria, baselines, held-out sets) is SHA-256-locked **before** models see test
data. Hash embedded in the manuscript (`manuscripts/paper1/prereg_hash.txt`).

## Pipeline (regenerates every atlas artifact)
```bash
# 1A — data ingestion
python -m pen_stack.data.genome                                 # hg38 1 kb grid
python -m pen_stack.data.ingest_chromatin --biosample K562      # (+ HepG2, CD34+ progenitor, mouse ES-Bruce4)
python -m pen_stack.data.ingest_safety_annot                    # COSMIC + DepMap + GENCODE
python -m pen_stack.data.ingest_integration --mode lafave --lafave-bed mlv_k562.bed.gz   # (+ hepg2; + VISDB)
python -m pen_stack.data.ingest_trip                            # GSE49806/49807

# 1B/1C — layers, atlas, validation (per cell type ct ∈ {k562,hepg2,hspc})
python scripts/p1_build_durability.py                           # conditional chromatin→expression (TRIP)
python scripts/p1_train_safety.py --ct $ct
python scripts/p1_build_atlas.py   --ct $ct                     # → atlas_$ct.parquet + safe-harbour sanity
python scripts/p1_export_tracks.py --ct $ct                     # → BigWig + BED
python scripts/p1_validation_report.py --cts k562 hepg2 hspc    # → validation_report.json (all checks pass)
```

## Tests & CI
`pytest -q` → 21 unit tests (schema, no-override, universe consistency, scorecard, smoke). GitHub Actions runs
`ruff check pen_stack tests` + `pytest` on every push (green). Heavy integration steps run on the VM, not CI.

## Model / data cards
`docs/cards/{safety,durability,atlas}.md` — intended use, training data, metrics, **known failure modes**
(safety-label circularity; durability partial-panel transfer; reachability locus-level), decision-support scope.

## Data release
Atlas parquets, BigWig/BED tracks, models, and feature stores deposited to Zenodo (see
`phase_1/zenodo_deposit_files/`, with `MANIFEST.tsv` + `checksums.sha256`). Verify: `sha256sum -c checksums.sha256`.

## Determinism
LightGBM `random_state=42`; GroupKFold by chromosome. `pen_stack.atlas.universe.assemble()` is deterministic
(regression-tested). Atlas builds are reproducible to within model-training tolerance from the pinned sources.
