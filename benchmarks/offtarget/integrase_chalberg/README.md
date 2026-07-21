# PhiC31 pseudo-attP learned predictor, full Chalberg 2006 115-site set

**Question:** does a learned model over sequence/architecture features recover the documented human phiC31
genomic pseudo-attP sites above BOTH (a) canonical-attP sequence-similarity and (b) the palindrome-only feature?

This benchmark supersedes the earlier **N=3 open-GenBank subset** sealed negative
(`benchmarks/offtarget/integrase/`, Thyagarajan 2001 psiA/psiC/psiD) with the **full 115-site Chalberg 2006
genomic pseudo-attP set**, which was obtained and evaluated at proper statistical power.

## Data
- **Positives:** 115 genomic phiC31 pseudo-attP sites, **Chalberg et al. 2006** (*J Mol Biol* 357:28-48,
  **PMID 16414067**) supplement **`mmc1.xls`**, coordinates **hg17** (confirmed from paper methods; sequences
  extracted directly from `hg17.2bit`, no liftover). Cell lines 293/D407/HepG2. All 115 yielded clean +/-50 bp
  (100 bp) windows.
- **Negatives:** 2,225 **GC-matched** (within +/-2%) genomic decoy windows, >=1 kb from any positive
  (~20 per positive).
- **Features (68):** dyad-symmetry palindrome score, inverted-repeat stem length, central AT content,
  canonical-attP consensus similarity (the sealed-negative method, PDB 9U2T motif), 3-mer composition.
- **Model:** LightGBM, **leave-one-chromosome-out** CV (115 sites across 23 chromosomes; spatial-leakage guard).
- **Baselines:** attP-similarity-only, palindrome-only. **Metrics:** AUROC + AUPRC, 2,000x bootstrap CI of
  (model - baseline).

## Results (`metrics.json`)
| Score | AUROC | AUPRC (prevalence 0.049) |
|---|---|---|
| **Learned model** | **0.637** | **0.215** |
| attP-similarity (sealed-negative method) | 0.632 | 0.094 |
| palindrome-only | 0.545 | 0.055 |

Bootstrap 95% CI of (model - baseline):
- vs attP-similarity: **AUROC diff [-0.054, 0.065]** (includes 0), **AUPRC diff [0.051, 0.192]** (excludes 0).
- vs palindrome: **AUROC diff [0.017, 0.170]** (excludes 0), **AUPRC diff [0.093, 0.240]** (excludes 0).

**Sealed verdict: `learned_model_null`.** The strict pre-registered bar was *beat BOTH baselines on BOTH metrics
with CI excluding 0*; the model does not clear it because it does not improve AUROC over attP-similarity.

## Interpretation
- **A null on the strict both-metrics criterion.** The model does not beat attP-similarity on AUROC
  (diff CI [-0.054, 0.065] includes 0), so it is a formal `learned_model_null`.
- **A real precision-recall gain.** Finding pseudo-attP is a rare-positive retrieval task (prevalence 0.049); on
  AUPRC the learned model beats **both** baselines with CI excluding 0 (**0.215 vs 0.094 / 0.055**, ~2-4x the
  baselines, >4x prevalence).
- **What the null teaches:** at N=115 the attP-**similarity** baseline is itself a moderate predictor
  (AUROC 0.63) - so the N=3 open-subset "sequence identity fails" conclusion does **not** generalize; identity
  carries real ranking signal and the learned model matches (not beats) it on AUROC while improving precision.
- **Decoy caveat:** negatives are GC-matched (a relatively easy decoy). The AUPRC win is method-comparative
  separability, not an in-vivo integration-rate model or a genome-wide FDR.

Reported as a truthful negative on the strict rule with a genuine, CI-clean precision-recall gain. Run once, not
retuned. Pre-registered and sealed before scoring: `p3_prereg.sealed.json` =
`405d740fe9ccb154a18f69aed9886c87586f2326ee851ed75c7fc8e42904f9fe`.

## Provenance
All numbers in `metrics.json` are copied verbatim from the sealed P3 result set; this directory redistributes those
numbers into the pen-stack benchmark tree and performs no new computation.
