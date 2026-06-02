# Data Card — The Writable Genome atlas

**Artifacts:** `atlas_{k562,hepg2,hspc}.parquet` + BigWig/BED tracks · **Phase 1, Steps 1.9–1.11**
**Release:** Zenodo (DOI on upload) · CC-BY-4.0 (tracks) · MIT (code)

## What it is
A genome-wide, decomposable **writability** atlas: **3,031,030 loci × 3 cell types** (K562, HepG2, CD34+ HSPC),
1 kb resolution, hg38. `writability = 0.5·safety + 0.5·p_durable` with components retained.

## Schema (`atlas_<ct>.parquet`)
`chrom, bin` (position = bin×1000) · `safety` (1−P(genotoxic)) · `pred_expression` · `p_durable`
(P(durable|epigenome)) · `reachable_tier1` (locus-level Tier-1 writer families) · `writability`.

## Provenance (all public)
hg38 (UCSC) · ENCODE bigWig signal (accessibility + 5 histones; K562, HepG2, CD34+ common myeloid progenitor,
mouse ES-Bruce4) · GENCODE v46 · COSMIC CGC v104 · DepMap 26Q1 · LaFave 2014 MLV (NHGRI GeIST) · VISDB ·
TRIP GSE49806/49807 · UniProt/Pfam (WT-KB). Accessions pinned in `configs/datasets.yaml`.

## Validation (blind, pre-registered)
All pre-registered checks pass (`validation_report.json`). Safe harbours score high, clinical genotoxic CIS low:

| Cell type | safe-harbour writability %ile | genotoxic-CIS %ile |
|---|---|---|
| K562 | 0.586 | 0.013 |
| HepG2 | 0.554 | 0.012 |
| CD34+ HSPC | 0.570 | 0.108 |

## Known limitations
- **Reachability** is released at the **locus level** (`reachable_tier1`): Tier-1 reprogrammable writers
  (bridge/Cas9/Cas12a) are broadly available at 1 kb; fine-grained per-site reachability is a design-time
  concern handled by the Write Planner (Phase 3).
- **Sequence-derived features** (pretrained ChromBPNet/Borzoi inference, Step 1.5) are **not** included in this
  release — an optional enrichment, deferred; the atlas validates without them.
- Cross-cell-type writability varies locus-by-locus (e.g. AAVS1 0.78–0.88) — the quantified function-transfer
  behaviour, reported as a result.
- Compares favourably to criteria-based safe-harbour lists by being *learned, durability-aware, and writer-coupled*.

## Intended use
Rank candidate insertion loci for genome-writing projects; surface safe + durable + reachable sites. Inputs to
the Write Planner. **Decision-support, not a clinical directive** — every score traces to public data + a
pre-registered model.
