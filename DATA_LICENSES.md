# PEN-STACK: Data Licenses & Provenance

**The rule:** the released artifact ships **open data only** (CC0 / CC-BY / public-domain). License-restricted
sources (**OncoKB, COSMIC**) are **never committed, never used as training data**; they are *optional, local-only*
enrichers a registered user pulls under **their own license** via `scripts/fetch_licensed_sources.py`, for validation
only. A CI test (`tests/unit/test_data_licenses.py`) fails if a restricted source appears as a shipped *derived-data*
source.

> Not legal advice. The "is a derived statistic / trained model a redistribution?" question is genuinely unsettled;
> this is a conservative engineering policy. Everything shipped is CC0/open.

## Shipped sources (open: vendored or build-time)

| Source | What it provides | License | Train ML? | Redistribute? | Used in |
|---|---|---|---|---|---|
| **CancerMine** (Lever et al. 2019, *Nat Methods* 16:505, [10.1038/s41592-019-0422-y](https://doi.org/10.1038/s41592-019-0422-y); Zenodo 7689627) | oncogene / TSG / driver gene list (+ citation counts) | **CC0** | yes | yes | `data/ingest_safety_annot.py::load_cancermine` → `safety_annot` → `safety_{ct}.pkl`, `genotoxicity_oracle.yaml`, atlas |
| **DepMap** (Broad, CRISPRGeneEffect) | common-essential genes | **CC BY 4.0** | yes | yes (attrib) | `load_depmap_essential` → `dist_essential` |
| **Leemans 2019** (Cell, [10.1016/j.cell.2019.03.009](https://doi.org/10.1016/j.cell.2019.03.009); PMID 30982597) | human K562 TRIP position-effect: the authors' feature set, expression, LAD call, promoter name and class, plus the integration coordinates from their supplement | **CC BY-NC-ND 4.0** (supplement); **no licence declared** (their GitHub feature set) | yes | **nothing redistributed**: both sources are fetched at build time by `scripts/build_leemans_input.py` (see note) | `p2_build_human_head.py` → `benchmarks/position_effect_human/leemans_scored_input.parquet` → `position_effect_human_k562.pkl` |
| **gnomAD** (pLI / LOEUF) | dosage / constraint | open (aggregate) | yes | yes | locus dosage signals |
| **ClinVar / ClinGen** | dosage sensitivity | public domain (NCBI/NIH) | yes | yes | locus dosage signals |
| **GENCODE / Ensembl** (v46) | gene/TSS coordinates | open | yes | yes | `parse_gencode_genes` → all distances |
| **VISDB** (Zhao et al. 2020, [10.1093/nar/gkz867](https://doi.org/10.1093/nar/gkz867)) | viral integration-site catalogues | academic/open | yes | summary-only shipped | `p52_build_genotox_oracle.py` (per-class enrichment) |
| **Pfam / InterPro** | protein function families | open | yes | yes (accessions) | Guardian signature screen |
| **Select-Agent / Australia-Group** lists | controlled-agent taxa | public (regulatory) | yes | yes | Guardian |

The genotoxic-CIS gene names (LMO2/MECOM/EVI1/CCND2/PRDM16/HMGA2) are **well-known literature facts**, not COSMIC-specific.

**Leemans 2019 (position-effect head).** This repository ships none of it. `benchmarks/position_effect_human/leemans_scored_input.parquet` is **not committed**; `scripts/build_leemans_input.py` fetches both upstream sources and joins them locally, which is
what CC BY-NC-ND 4.0 permits, since the licence allows producing adapted material and not sharing it.

The table has two upstream sources, and every column is theirs:

| Columns | Source | Terms |
|---|---|---|
| the five `*_mean` marks, `LMNB1_DamID`, `lad`, `prom_name`, `class`, `expr_y`, and the `barcode` index | `github.com/vansteensellab/Promoters_in_LADs`, `data/cl20181013_feature_set_trip.Rdata` (objects `X`, `y`, `lad_vec`) | **no licence declared** |
| `chrom`, `pos` (hg19) | Cell supplement Dataset S2, `mmc4.zip -> Dataset_S2_TRIP.tsv`, served by Europe PMC for the open-access record | CC BY-NC-ND 4.0 |

The 9,298 rows are the row count of the authors' own feature matrix, not a filter applied here: the hPGK pool is absent upstream. The barcode join to the coordinate table is exact at 9,298 of 9,298, and the coordinates are hg19 as the supplement states, with no liftover applied. Our only contribution is that join and the selection of five of their fourteen marks.

`build_leemans_input.py` asserts the rebuilt table against a recorded content digest, so a reader can confirm they have the same values the paper used without this repository carrying them.

`benchmarks/position_effect_human/leemans_scored_input.parquet` is a derived feature table: per-integration measured expression and the escaper/repressed call from Leemans et al., lifted to hg38 and joined to ENCODE chromatin signal computed here. It is committed for one purpose, to let `make repro-human` recompute the single reported correlation on a bare clone, and Leemans et al. are attributed wherever it is used.

Whether a derived feature table of this kind is a redistribution of the source compilation is not settled, and this note records the position rather than resolving it. Copyright in most jurisdictions does not reach measured values as such; the EU and Dutch *sui generis* database right does reach substantial extraction from a database regardless of originality, and the promoter assignment and the escaper/repressed call are the authors' calls rather than facts about the genome.

Any use beyond reproducing the result reported here should take the data from its source: the Cell supplement under its own terms, or the underlying reads, which are public domain in SRA under `PRJNA504533`. A reader who prefers to build the table from their own copy of the supplement joins Dataset S2 to the ENCODE marks on hg38 coordinates using the column names in `scripts/p2_build_human_head.py`; the committed file's digest is in `benchmarks/position_effect_human/SHA256SUMS`, so a rebuild can be checked against it.

**gnomAD.** This project includes data from the gnomAD release (Karczewski et al. 2020, [10.1038/s41586-020-2308-7](https://doi.org/10.1038/s41586-020-2308-7)); the gnomAD team requests this acknowledgment.

## Restricted sources, NOT shipped (local-only, your own license, validation-only)

| Source | License | Status in PEN-STACK |
|---|---|---|
| **COSMIC Cancer Gene Census** | free w/ registration, **NO redistribution**; commercial = QIAGEN | **Out of the shipped artifact.** `load_cosmic()` exists but is **off by default**; available via the BYO-license fetcher for local enrichment under your own license. *Citations of COSMIC methodology are fine.* |
| **OncoKB** | **no ML training, no redistribution**; academic API license | **Out of the artifact entirely.** Benchmarking/validation only, **with written permission**, local-only (`cancerGeneList.tsv` is never committed). |

## Bring-your-own-license enrichment
`scripts/fetch_licensed_sources.py` automates a **registered** user's own licensed download of COSMIC/OncoKB into a
gitignored `licensed_data/`. The repo never contains that data. Re-run the safety build with `--source cosmic` to use it
locally. This swaps only the *source* of the same facts, with no capability changes.

## Provenance note (the legal crux)
Copyright/IP does **not** protect the *fact* that a gene is an oncogene, only the *compiled database* (and, in the EU,
the *sui generis database right* over substantial extractions). PEN-STACK sources the oncogene/TSG **list** from a **CC0
compilation (CancerMine)** instead of COSMIC's file. CancerMine catalogues more genes than CGC (text-mined; ~2,400
oncogenes / ~2,000 TSGs vs ~700); a `min_citations` threshold tunes precision. For a *flagging* tool that routes to human
review, broader coverage is acceptable/preferable.
