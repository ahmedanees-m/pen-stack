# Model Card - Safety layer (genotoxicity risk)

**Module:** `pen_stack.wgenome.safety` | **Models:** `safety_{k562,hepg2,hspc}.pkl` | **Phase 1, Step 1.6**

## Intended use
Score a 1 kb genomic locus for **insertional-genotoxicity risk** in a given cell type, as one decomposable
input to the writability profile. **Decision-support, not a clinical directive.**

## Architecture
Calibrated gradient-boosted classifier (LightGBM + isotonic calibration), **chromosome-block GroupKFold**
cross-validation so adjacent bins never leak between train/test. Output: a calibrated `P(genotoxic)`;
the atlas uses `safety = 1 - P(genotoxic)`.

## Training data (per cell type)
- **Features:** unified `accessibility` (ATAC->DNase) + 5 histone marks (ENCODE) | log distances to nearest
  oncogene / TSG / essential gene / TSS (COSMIC CGC v104 + DepMap 26Q1 + GENCODE v46) | integration density
  (LaFave 2014 MLV for K562/HepG2; VISDB retroviral propensity for HSPC).
- **Label:** proximity to a validated genotoxic common-integration site (LMO2, MECOM/EVI1, CCND2, PRDM16, HMGA2).

## Metrics (held-out, per cell type)
| Cell type | safety AUROC | features | concordance (safe-harbour %ile vs genotoxic-CIS %ile) |
|---|---|---|---|
| K562 | 0.80 | accessibility+5 histone+4 dist+integration | 0.586 vs 0.013 |
| HepG2 | 0.81 | same | 0.554 vs 0.012 |
| CD34+ HSPC | 0.80 | same (VISDB integration fallback) | 0.570 vs 0.108 |

## Known limitations / failure modes
- **The `genotoxic_cis` AUROC is partly circular** (label = proximity to 5 oncogenes ~ the distance baseline).
  The *meaningful* metric is concordance: the learned model's value is **safe-harbour discrimination** - it
  correctly flags AAVS1 as safe where a naive distance rule over-flags it - not re-ranking known oncogenes.
- **Integration feature matters:** without an integration feature, the safety model degrades to ~chance
  (HSPC AUROC 0.50 -> 0.80 once the VISDB integration feature is supplied). Cell types lacking integration
  data fall back to the cell-type-agnostic VISDB track.
- Yields **risk, not certainty**; genotoxicity also depends on cargo/promoter design (a separate, composable
  factor handled by the Planner). Integration-outcome data come from semi-random vectors; position-effect
  physics transfers, absolute risk transfers only partially.

## Ethical / scope
Outputs are candidate risk estimates requiring expert validation. Not for clinical decisions.
