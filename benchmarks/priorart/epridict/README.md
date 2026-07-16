# Analysis A, durability axis vs ePRIDICT efficiency (distinctness)

**Prereg:** [`prereg/ws_priorart.yaml`](../../../prereg/ws_priorart.yaml) (SHA-locked
`fa55cb709fb90c60d0a55ee4530529cf452ba7a6d56e54a220e52e92890929fb`, written *before* the ePRIDICT
scores existed).

## Question
On a shared set of K562 loci, is the PEN-STACK **durability** score (`p_durable`) a **distinct/complementary**
signal, or is it largely **re-deriving** ePRIDICT's **efficiency** score? Endpoints differ (efficiency vs
durability); this measures *distinctness only*, never superiority on either tool's own endpoint.

## Result (reported verbatim)

| statistic | value | 95% CI (10,000-resample bootstrap) |
|---|---|---|
| Spearman ρ | **0.212** | [0.188, 0.235] |
| Pearson r | 0.202 | [0.179, 0.224] |
| Variance partition R² (`p_durable ~ efficiency`) | **0.041** | [0.032, 0.050] |
| **Unexplained fraction (added signal)** | **0.959** | - |
| n shared K562 loci (scorable by both) | **7,295** | of 8,000 (705 ePRIDICT feature-missing) |

**Decision (pre-registered rule): `DISTINCT`**, `|ρ| = 0.21 < 0.30` **and** `R² = 0.04 < 0.10`.

ePRIDICT's efficiency score explains **~4%** of the durability axis's variance; **96% is unexplained**. The
faint positive slope is expected, both models read K562 chromatin and share three marks (H3K4me1, H3K9me3,
H3K27me3), but the effect size is negligible (Cohen), so the axes are distinct/complementary.

**Caveat.** At n = 7,295 the correlation is *statistically* significant (p ≈ 1e-75): the two axes are
not perfectly independent. The claim is **weak correlation / negligible shared variance**, i.e. distinctness,
not statistical independence. The variance partition (96% unexplained) is the load-bearing number.

## Manuscript consequence (pre-registered)
`DISTINCT` → **keep** the durability axis as a distinct/complementary contribution (softened wording);
proceed to GSH-recovery + GEG-SH concordance.

## How it was produced
1. **Loci**, 8,000 bins sampled uniformly (seed 20260702, 6-bin edge trim) from the authoritative hg38 1-kb
   K562 durability atlas `phase_1/out/atlas_k562.parquet`; `position_hg38 = bin*1000 + 500`.
   `p_durable` read directly from the atlas (the committed model output; no re-scoring). See
   [`data/priorart/loci_gen.csv`](../../../data/priorart/loci_gen.csv) +
   [`loci_pdurable_gen.parquet`](../../../data/priorart/loci_pdurable_gen.parquet).
2. **ePRIDICT efficiency**, ePRIDICT-light (6 K562 ENCODE bigWig tracks) run on the VM in the
   `epridict:tools` Docker image over the 8,000 loci (16-way parallel), output column
   `ePRIDICT score (light model)`. Raw output: `epridict_raw_output.csv`.
3. **Distinctness**, inner-join on (chromosome, position_hg38), drop ePRIDICT feature-missing rows, then
   Spearman/Pearson + OLS variance partition + 10,000-resample bootstrap CIs. See `epridict_orthogonality_metrics.json`.

## Limitations
- **Endpoint mismatch**: ePRIDICT = efficiency, PEN-STACK = durability. Distinctness, not superiority.
- **Single-timepoint durability**: `p_durable = 1 - P(silenced)` from a lower-quartile expression split, not a
  measured silencing-over-time trajectory (settled gate).
- **Shared lineage**: both models derive from ENCODE K562 chromatin and share 3 marks → the test is conservative.
- **Domain shift**: the durability model is TRIP-trained on mouse mESC chromatin, applied to human K562 marks.

## Files
| file | description |
|---|---|
| `epridict_orthogonality_metrics.json` | all statistics + CIs + the decision + input SHAs |
| `orthogonality_scatter.png` | figure: p_durable vs efficiency on the 7,295 shared loci |
| `shared_loci_scores.csv` | the 7,295 paired scores (epridict_efficiency, p_durable, chrom, pos) |
| `epridict_raw_output.csv` | raw ePRIDICT-light batch output over all 8,000 loci (incl. feature columns) |
| `SHA256SUMS` | integrity hashes for the above |
