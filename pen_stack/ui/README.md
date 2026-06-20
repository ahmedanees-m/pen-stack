# PEN-STACK UI - The Writable Genome browser

A scientific Streamlit front-end over the genome-wide writability atlas.

## Pages
- **Overview** - concept, KPIs, writability distribution, the three layers, validation summary.
- **Forward query** - gene/coordinate -> decomposed verdict (writability/safety/durability gauges + local track).
- **Site finder (inverse)** - disease gene -> top-N safest writable loci within a window (ranked table + map + CSV download).
- **Atlas browser** - genome-wide writability/safety/durability tracks by region.
- **Validation** - safe-harbour vs genotoxic-CIS concordance + durability metrics (the figure panels).
- **Cross-cell-type** - K562 <-> HepG2 transfer, reported honestly.
- **Writer Atlas** / **Write Planner** / **Bridge design** - enzyme catalogue, inverse design, bridge RNA + off-target.

### v3.1 additions
- **Guide QC** - rank bridge-RNA guide variants by fold-QC + off-target; a synthetic positive-control panel (hand-constructed guides, not real outcomes) checks that each constructed failure mode ranks below a clean control.
- **Cargo Polish** - scan a cassette for silencing/instability triggers (CpG islands, GC, cryptic splice, MFE, silencers) with a fix per flag.
- **Multiplex risk** - pairwise translocation-risk screen for a 2-5 edit plan (DSB-free recombinase plans carry ~zero risk).
- **PEN-Agent** - the grounded write-planning state machine (site -> writer -> cargo+polish -> off-target -> 3D risk -> report), with per-step provenance and zero fabrication.
- **Genome-Writing Bench** - the v0.1 leaderboard (planner vs naive vs a grounded LLM agent).

## Run
```bash
pip install streamlit plotly pandas pyarrow numpy
# point at the atlas outputs (must contain atlas_<ct>.parquet, gene_coords.parquet, validation_report.json)
export PEN_ATLAS_DIR=/path/to/phase_1/out
streamlit run pen_stack/ui/app.py
```
Data files: `atlas_k562.parquet`, `atlas_hepg2.parquet`, `gene_coords.parquet`, `validation_report.json`.

## Figures from the UI
Forward-query gauges (AAVS1), site-finder map (HBB  +/- 1 Mb), and the Validation page's safe-harbour-vs-genotoxic
bar chart are publication-ready screenshots; pair them with the ROC/Spearman curves from `validation_report.json`.
