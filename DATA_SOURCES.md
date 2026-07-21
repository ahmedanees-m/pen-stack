# Data sources and provenance

This file is the human-readable index of every external dataset PEN-STACK uses, with its accession or DOI and
its role. Machine-readable pins (versions, retrieval dates, checksums) are in
[`configs/datasets.yaml`](configs/datasets.yaml); licensing and the open-data policy are in
[`DATA_LICENSES.md`](DATA_LICENSES.md).

## How the data is distributed

- **Committed in the repository:** small curated tables (`data/curated/`), the one-chromosome demo atlas
  (`data/demo/`), the committed benchmark metrics and frozen splits (`benchmarks/*/`), the offline transcript
  cache (`data/llm_bench_cache/`), and the derived Leemans K562 features table
  (`benchmarks/position_effect_human/leemans_scored_input.parquet`, 0.5 MB) that `make repro-human` uses to
  **recompute the headline expression-robustness result from source**. These let a fresh clone run the
  quickstart, recompute the headline number, and replay every benchmark with no download.
- **Fetched from the Zenodo deposit** with `scripts/fetch_artifacts.sh` (set `ZENODO_DOI`): the full
  genome-wide Writable-Genome atlases (`atlas_{k562,hepg2,hspc}.parquet`), their BigWig tracks and top-site
  BED files, `gene_coords.parquet`, and the trained models (`durability.pkl`, `safety_{ct}.pkl`, the
  position-effect heads, `capsid_fitness.pkl`). These are derived products, released open.
- **Referenced by accession only, never re-hosted:** licensed or large raw third-party data. Provenance
  below; retrieval is the user's own, under the source's own terms.

## Public sources (open; committed or build-time)

| Source | Accession / DOI | Role |
|---|---|---|
| Human genome GRCh38 (hg38) | UCSC / Ensembl | primary coordinate system |
| Mouse genome mm10 | UCSC | TRIP mouse data and the cross-species transfer test |
| ENCODE chromatin | ENCODE portal (incl. ENCFF529BOG) | ATAC, DNase, and histone marks for K562, HepG2, CD34+ progenitor, and mouse ES-Bruce4 |
| Roadmap Epigenomics | egg2.wustl.edu/roadmap | additional chromatin context |
| GENCODE v46 | gencodegenes.org | gene models and coordinates |
| DepMap Public 26Q1 | depmap.org | gene essentiality |
| CancerMine | Lever et al. 2019, doi:10.1038/s41592-019-0422-y; Zenodo 7689627 (CC0) | oncogene / tumour-suppressor annotation (default safety source) |
| LaFave 2014 MLV integrations | doi:10.1073/pnas.1413620111 | integration-site reference |
| VISDB | viral integration site database | integration-site reference |
| UniProt, Pfam, InterPro | uniprot.org / interpro (Pfam) | writer-enzyme families and the local domain screen |
| Europe PMC | europepmc.org | literature grounding for the retrieval corpus |
| Addgene | addgene.org | plasmid and enzyme metadata |

## Position-effect and off-target measured data

| Source | Accession / DOI | Role |
|---|---|---|
| TRIP (Akhtar et al. *Cell* 2013) | GEO GSE49806 / GSE49807; doi:10.1016/j.cell.2013.07.018 | mouse mESC position-effect (cross-species null) |
| Leemans et al. K562 TRIP (*Cell* 2019) | doi:10.1016/j.cell.2019.03.009 | human K562 position-effect (the external validation of the expression-robustness axis) |
| Chalberg et al. genomic pseudo-attP (*J Mol Biol* 2006) | doi:10.1016/j.jmb.2005.11.098 | phiC31 integrase off-target benchmark |
| phiC31 pseudo-attP records | GenBank AF333429 / AF333430 / AF333431 | integrase off-target reference |
| Perry 2025 bridge-recombinase off-target and DMS | source publication (kept local; only derived products released) | bridge off-target engine |
| Genome-wide nuclease off-target assays | CHANGE-seq, SITE-seq, CIRCLE-seq, GUIDE-seq (per-study accessions in `configs/datasets.yaml`) | nuclease off-target validation |
| FLIP-AAV | benchmark release | capsid-fitness comparison |

## Licensed or restricted sources (by accession only; never committed, never training data)

| Source | Terms | Role |
|---|---|---|
| COSMIC Cancer Gene Census | registered download under COSMIC licence | optional, local-only safety enricher (off by default) |
| OncoKB | OncoKB licence | optional, local-only benchmark reference |

These are pulled by a registered user with `scripts/fetch_licensed_sources.py` under the user's own licence,
for local validation only. A CI test (`tests/unit/test_data_licenses.py`) fails if a restricted source ever
appears as a shipped derived-data source. See [`DATA_LICENSES.md`](DATA_LICENSES.md) for the full policy.

## The Zenodo deposit

The archived version of record and its supporting data are on Zenodo (concept DOI in the manuscript and
`CITATION.cff`). The deposit contains the derived data described above (atlases, tracks, models), the frozen
benchmark splits with their SHA-256 locks, the pre-registrations, the data and model cards, the offline
oracle cache, and a snapshot of the tagged source. Licensed raw data is listed by accession only.
