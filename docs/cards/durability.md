# Model Card - Durability layer (conditional chromatin-context model)

**Module:** `pen_stack.wgenome.durability` | **Model:** `durability.pkl` | **Phase 1, Step 1.7**

## Intended use
Predict whether an **inserted cassette will stay expressed** at a locus, from the *local chromatin context* -
the writing-relevant quantity no existing safe-harbour resource provides. One decomposable input to writability.

## Architecture & key property
Two LightGBM heads learning **one function**: `local chromatin features -> (expression level, P(durable))`.
The model **never sees a genomic coordinate** - only the epigenome at the integration. It is therefore
**cell-type-agnostic in function, cell-type-specific in inputs**: to score a new cell type you supply its
chromatin tracks. Chromosome-block CV; trained once, applied to any epigenome (the mouse->human transfer).

## Training data
- **Supervision:** TRIP - Thousands of Reporters Integrated in Parallel (Akhtar et al. 2013, *Cell*; GEO
  **GSE49806** tet-O + **GSE49807** mPGK; mouse mESC, mm9). **11,433 integrations** with position-tagged
  reporter expression + silenced/stable label.
- **Features:** 5 histone marks (H3K27ac, H3K4me1, H3K4me3, H3K9me3, H3K27me3) point-queried from mouse
  **ES-Bruce4** ENCODE bigWigs (mm10) at each lifted integration ( +/- 2.5 kb).

## Metrics (held-out, chromosome-block CV)
| Metric | Model | Baseline | Pre-registered |
|---|---|---|---|
| expression Spearman rho | **0.423** | (ATAC n/a) | >= 0.30 (met) |
| silenced/stable AUROC | **0.643** | H3K9me3-only 0.578 | beats baseline (met) |

Top features: H3K4me3 (active promoter, ^ expression), H3K9me3 (heterochromatin, ^ silencing), H3K4me1,
H3K27me3, H3K27ac - biologically sensible.

## Transfer & graceful degradation (reported, not hidden)
Applied to human K562/HepG2/HSPC epigenomes via the **same 5 histone marks**. **Robust to partial panels:**
missing tracks are passed as NaN (LightGBM-native) - CD34+ HSPC lacks ATAC yet has all 5 histones, so durability
runs at full strength there (HSPC validated *best* of the three cell types).

## Known limitations
- Trained with **5 histone marks, no accessibility** (ES-Bruce4 lacks ATAC/DNase on mm10), a partial
  panel; adding accessibility would likely raise rho.
- Mouse->human transfer assumes comparable bigWig signal scaling; reported as a finding, not assumed.
- Some position effects are long-range/3D (enhancer reach > 20 kb) and not captured by local features.

## Scope
Predicts position-effect *probability*, not a universal expression guarantee. Decision-support only.
