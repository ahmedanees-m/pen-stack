# Genotox-Panel: the integrated safety filter vs documented clinical genotoxic loci (RB-2)

This benchmark records how the shipped **integrated locus score** (K562 atlas `writability` + calibrated `safety`,
per 1 kb bin) behaves on a panel of **documented clinical insertional-oncogenesis loci** from real gene-therapy
trials, versus functionally-validated safe harbors. It is the RB-2 result from the retrospective-validation work,
landed here as a real, source-locked benchmark. Previously it lived only in the working area
(`Retrospective_validation/`).

Every number in `metrics.json` is copied verbatim from a source file, and each field is annotated with its origin in
`metrics.json -> field_sources`. Source files are listed under `metrics.json -> source_files`.

## What this is (and is not)

This is **confirmatory face-validity, not a novel AUROC.** Per the sealed anti-circularity manifest
(`fce43e1c68082b8a72f1a8a0492a08285a1954336bd6adc3e52a1be6281b9e38`, sealed 2026-07-05 **before** scoring), the score
rejects annotated oncogenes **by construction** - the CancerMine `dist_oncogene` / `genotoxic_cis` layer. So a headline
separation number is not the informative content. The informative content is: is there a **non-obvious subset**, are
there **false-negatives**, and does the risk band **track severity**?

## The panel

- **8 genotoxic loci** (real trial insertional-oncogenesis): LMO2, CCND2, MECOM/EVI1, PRDM16, HMGA2, SETBP1, BMI1,
  MN1 (corpus + trial citations in `../../../Retrospective_validation/rb_corpus_starter.csv`).
- **1 control**: IKZF1 (Fabry non-persistent integration near IKZF1, <0.15%, did not persist - a near-oncogene
  negative-outcome control).
- **8 functionally-validated safe harbors**: AAVS1, CLYBL, CCR5, hRosa26, H11, Pansio-1, Olonne-18, Keppel-19.

Writability: higher = safer (safe harbors ≈ 99th percentile, hard-coded oncogenes ≈ 0th). `flagged_by_filter` is
derived as `safety == 0.0` (safety 1.0 = passes the filter).

| locus | class | CancerMine | severity | writ_pct | safety | genotoxic_cis | flagged |
|---|---|---|---|---|---|---|---|
| LMO2 | genotoxic | oncogene,driver | severe | 2.5 | 0.0 | True | yes |
| CCND2 | genotoxic | oncogene,driver,TSG | severe | 2.6 | 0.0 | True | yes |
| MECOM | genotoxic | oncogene,driver | severe | 2.4 | 0.0 | True | yes |
| PRDM16 | genotoxic | oncogene,TSG | moderate | 2.4 | 0.0 | True | yes |
| HMGA2 | genotoxic | oncogene,driver,TSG | **mild** | **0.0** | 0.0 | True | yes |
| **SETBP1** | genotoxic | oncogene,driver | moderate | **44.6** | **1.0** | False | **no (FN)** |
| **BMI1** | genotoxic | oncogene,driver,TSG | **severe** | **99.9** | **1.0** | False | **no (FN)** |
| **MN1** | genotoxic | oncogene,driver,TSG | moderate | **34.3** | **1.0** | False | **no (FN)** |
| IKZF1 | control | oncogene,driver,TSG | none | 2.6 | 0.0 | False | yes |
| safe harbors (8) | safe_harbor | (not oncogenes) | safe | median **73.0** | 1.0 | False | no |

Genotoxic median writ_pct **2.5**; safe-harbor median **73.0**. Face-validity separation (genotoxic writ_pct <
safe-harbor writ_pct) AUROC **0.797** (N = 8 vs 8) - dragged down by the three missed loci; confirmatory, not a novel
metric.

## Findings

1. **The clean separation is by construction.** The five loci the filter flags hard (LMO2/CCND2/MECOM/PRDM16/HMGA2,
   writ_pct ≤ 2.6, safety 0.0) are exactly the genes encoded in the score's own `genotoxic_cis` training label. The
   manuscript §3.5 "AUROC 1.0 on five oncogenes" is this subset - it confirms the filter *encodes* known-bad loci, not
   that it *predicts* genotoxicity.
2. **The genuine test exposes false-negatives.** There is **no non-obvious subset by annotation** - all 8 genotoxic
   genes are CancerMine oncogenes (SETBP1 and MN1 included, contrary to the plan's guess). But the loci **outside the
   hard-coded label - SETBP1, BMI1, MN1 - are NOT flagged** (writ_pct 34–99.9, safety 1.0), despite documented trial
   genotoxicity. **BMI1 (severe, leukaemic in SCID-X1) ranks at the 99.9th writability percentile** - the clearest
   miss. The oncogene-distance layer registers all three as oncogenes (`dist_oncogene = 0`), but the integrated
   writability under-weights that annotation relative to chromatin for loci outside its hard-coded label.
3. **Calibration does not track severity (inverted here).** The mildest event (benign HMGA2 clonal dominance) scores
   most extreme (writ_pct 0.0); the most severe (BMI1 leukaemia) scores safest (99.9).

## Result

> The integrated safety filter cleanly rejects the canonical genotoxic loci it **encodes**
> (LMO2/CCND2/MECOM/PRDM16/HMGA2, ≤ 2.6th writability percentile), but on the broader set of **documented clinical**
> genotoxic loci it **misses those outside its hard-coded label** - SETBP1, BMI1, MN1 are ranked writable/safe (BMI1
> at the 99.9th percentile) despite causing trial genotoxicity - and its risk band **does not track documented
> severity**. So the component is a **coarse reject-known-bad filter, not a calibrated genotoxicity predictor**, and
> RB-2 sharpens rather than rubber-stamps the §3.5 claim. **The three learned-model false-negatives (SETBP1, BMI1,
> MN1) are now closed by a deterministic blocklist overlay - see *The fix* below; the deployed filter flags all
> eight documented loci.**

## The fix: a deterministic reject-known-bad blocklist closes the false negatives

The three misses above (SETBP1, BMI1, MN1) were **outside the soft model's six-gene training label**
(`LMO2, MECOM, EVI1, CCND2, PRDM16, HMGA2`), so the learned `safety` score never learned to flag them. A soft
model is the wrong tool for a reject-known-bad job. The deployed filter now applies a **deterministic
blocklist** on top of the soft score: any 1 kb bin within 50 kb of a **documented clinical
insertional-oncogenesis gene** is set `safety = 0.0` by rule (`pen_stack/wgenome/genotoxic_blocklist.py`,
overlaying the atlas in `load_writability`).

The blocklist (`configs/safety/genotoxic_loci.yaml`, **8 genes**) is completed from an **independent** source -
the 2025 *Leukemia* review of vector genotoxicity (doi:10.1038/s41375-025-02585-8, which independently names
LMO2, MN1, CCND2, BMI1, MECOM/MDS1/EVI1, PRDM16, SETBP1) plus the primary trial reports - **not** from this
panel, so the loci are on the list because they are documented, not because they failed the test. After the
overlay **all eight documented loci are flagged** (`safety = 0.0`); **BMI1 no longer ranks at the 99.9th
percentile.** Residual false negatives on the documented clinical set: **0, by construction.**

This is a **completeness fix for a blocklist, not a new prediction claim.** A blocklist cannot be validated on
its own contents, so this panel is a **coverage check** ("does the filter flag every documented clinical
genotoxic locus?"), not an AUROC. Predicting genotoxicity for **novel** loci remains out of scope for this
component; that is the separate, harder, outcome-validated locus axis (BioFirewall CCGD, AUROC ~0.60).

## Companion - what the axis *can* discriminate

For context, `metrics.json -> companion_axis_discriminability_matched_controls` records the **positive-side**
discriminability of the *same* writability axis: safe-harbour discovery vs **feature-matched controls**, from the
blind GSH-discovery run - **AUROC 0.679 (95% CI [0.536, 0.825]), 16 positives vs 800 controls**. That is what the axis
can do (separate safe harbours from matched genome); it is **not** a genotoxicity-prediction number and does not
rescue the false-negatives above.

## Caveats (disclosed)

- **Confirmatory, not a novel AUROC.** Annotated oncogenes are flagged by construction; the informative content is the
  false-negatives and the calibration failure, not the separation number.
- **Safe-harbor negatives overlap the §3.5 validated-GSH set** → not fully independent on the negative side.
- **One representative bin per locus** (gene-TSS / coordinate bin); writability is the shipped K562 atlas score.
  Per-integration hg38 coordinate extraction for each trial insertion was not performed (TBD-extract per the corpus).
- Annotation stack = GENCODE v46 + CancerMine (CC0, ≥3 citations) + DepMap-essential - the shipped license-clean
  safety-annotation stack.

## Manuscript disposition

RB-2 is kept as the real §3.5 contribution of the retrospective work: §3.5 was rewritten to
"…a reject-known-bad safety filter, not a calibrated genotoxicity predictor", keeping the AUROC null, reframing the
AUROC 1.0 as **by construction**, and stating the false-negatives with BMI1 (99.9th percentile) as the vivid example.
The abstract was updated to match ("validated safety filter" → "reject-known-bad safety filter").

## Files

| file | description |
|---|---|
| `metrics.json` | the full panel + summary stats + companion axis discriminability, each field annotated with its source (`field_sources`) |
| `README.md` | this file |
