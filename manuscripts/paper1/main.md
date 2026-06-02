# The Writable Genome: a predictive, writer-aware atlas of safe and durable insertion sites

**Anees Ahmed Mahaboob Ali**
VIT University, Vellore · ahmedaneesm@gmail.com

**Target venues:** Nature Methods / Nature Biotechnology / Genome Biology
**Pre-registration:** `prereg/paper1.yaml`, SHA-256 `4d6d7f4f…a38e9` (locked before test data)
**Data & code:** https://github.com/ahmedanees-m/pen-stack · atlas DOI: Zenodo (this release)

---

## Abstract

Genome **writing** — inserting genes, flipping or excising kilobases, installing landing pads — is gated by two
questions no resource answers: *where* in the genome can one safely and durably write, and *which* enzyme can
reach that site. Existing "safe-harbour" shortlists are criteria-based, cover one cell type, and predict neither
expression durability nor enzyme reachability. We present the **Writable Genome**, a predictive, cell-type-aware,
writer-aware atlas that scores any locus for **writability = safety × durability × reachability**, learned blind
on bulk-downloadable public data. We score 3,031,030 loci at 1 kb resolution across three human cell types
(K562, HepG2, and CD34+ haematopoietic stem/progenitor cells). The atlas recovers validated safe harbours as
highly writable and clinical genotoxic loci as non-writable — **without training on those labels** (safe-harbour
writability percentile 0.55–0.59 vs genotoxic-common-integration-site 0.01–0.11). The durability layer — a
conditional chromatin-context model trained on Thousands of Reporters Integrated in Parallel (TRIP) position-
effect data — predicts integrated-cassette expression from local chromatin alone (Spearman ρ = 0.42) and
transfers across species and cell types, degrading gracefully on partial chromatin panels. All pre-registered
success criteria pass. The atlas, models, BigWig tracks, and a queryable browser are released openly.

---

## 1. Introduction

Editing tools tell a molecular biologist *how* to change a base; nothing tells them *where* they can write new
information and *which* enzyme can write it there. Each lab re-derives an ad-hoc safe-harbour shortlist from
inconsistent criteria; published efforts range from ~2,000 sites to 25, none predict expression durability from a
learned model, none are writer-aware, and most cover one cell type — the field states openly that "genomic
regions suitable for safe, long-term hosting and expression of these sequences have not been identified."

Writing is gated by **(Q1) where can you write** — a locus must accept an insert without disrupting an essential
gene or activating an oncogene (*safety*), and the cargo must stay expressed (*durability*) — and **(Q2) what can
write there** (*reachability*). We build the missing reference layer answering both. The contribution is the
**integration** of three layers with **writing-specific supervision** (position effects on an integrated cassette;
clinical integration outcomes) and **writer coupling**, not a new chromatin predictor; we stand on mature
sequence→chromatin models and do not claim to beat them at their task.

## 2. Results

### 2.1 A genome-wide, decomposable writability atlas (Fig. 1)
We define `writability = safety × durability × reachability`, keeping the three components visible rather than
collapsing them into one opaque number, and compute it for every 1 kb bin (chr1–22, X) in K562, HepG2 and CD34+
HSPC (3,031,030 loci each). *(Fig. 1: concept + architecture — UI Overview page.)*

### 2.2 Safety layer recovers safe-harbour discrimination (Fig. 2)
A calibrated gradient-boosted model (chromosome-block cross-validation) scores genotoxicity risk from oncogene/
essential-gene/TSS proximity (COSMIC, DepMap, GENCODE), chromatin, and retroviral integration density (LaFave
2014 3.7M MLV integrations; VISDB). Because clinical genotoxic loci *are* oncogenes, a naïve distance rule scores
them highly by construction; the learned model's value is therefore measured as **safe-harbour discrimination**:
it correctly ranks AAVS1 in the safest 3rd percentile where the distance baseline over-flags it (41st percentile).
The integration feature is load-bearing — ablating it collapses the model to chance (AUROC 0.50→0.80).
*(Fig. 2: safe-harbour vs genotoxic-CIS recovery — UI Validation page.)*

### 2.3 Durability layer learns position effects and transfers (Fig. 3)
We train **one function**, `local chromatin → (expression, P(durable))`, on 11,433 TRIP integrations (Akhtar 2013;
GEO GSE49806/49807), using five histone marks point-queried at each integration. The model never sees a
coordinate, so it applies to any epigenome. Held-out (chromosome-block CV): expression Spearman ρ = **0.42**
(pre-registered ≥0.30), silenced/stable AUROC **0.64**, beating an H3K9me3-only baseline (0.58). Feature
importances are biologically sensible (H3K4me3↑expression, H3K9me3↑silencing). The function transfers mouse→human
and degrades gracefully on partial panels (CD34+ HSPC lacks ATAC yet retains all five histones, validating best
of the three cell types). *(Fig. 3: TRIP ρ/AUROC + feature importance.)*

### 2.4 The integrated atlas recovers known truth, blind (Fig. 4, Table 1)
Combining the layers, validated safe harbours score highly writable and clinical genotoxic common-integration
sites score near zero — **blind**, never trained on these labels:

**Table 1 — blind concordance (writability percentile; all pre-registered checks pass).**
| Cell type | safe harbours (AAVS1, CCR5, CLYBL) | genotoxic CIS (LMO2, MECOM, CCND2) | safety AUROC |
|---|---|---|---|
| K562 | 0.586 | 0.013 | 0.80 |
| HepG2 | 0.554 | 0.012 | 0.81 |
| CD34+ HSPC | 0.570 | 0.108 | 0.80 |

*(Fig. 4: the writable-genome map + site-finder near a disease gene, e.g. HBB — UI Forward/Site-finder pages.)*

### 2.5 Cross-cell-type transfer, reported honestly (Fig. 5)
Writability correlates across cell types yet differs locus-by-locus (AAVS1: 0.78–0.88). We report this as a
quantified function-transfer result, including the tighter margin on the partial-panel HSPC, rather than as a
footnote. *(Fig. 5: K562↔HepG2 transfer + comparison to criteria-based safe-harbour lists — UI Cross-cell-type page.)*

## 3. Methods (summary)
Per `docs/REPRO.md` and `docs/cards/`. hg38 1 kb grid; ENCODE chromatin (unified accessibility + 5 histones);
COSMIC v104 / DepMap 26Q1 / GENCODE v46 safety annotations; LaFave 2014 MLV (hg19→hg38) + VISDB integration;
TRIP GSE49806/49807 (mm9→mm10) durability supervision; Writer-Targeting Knowledge Base (8 families, tiered) for
reachability. Models: calibrated LightGBM (safety, chromosome-block CV), conditional LightGBM (durability).
Pre-registration SHA-locked before test. All heavy steps in one Docker image; pipeline in `scripts/p1_*`.

## 4. Discussion
The Writable Genome supplies what criteria-based safe-harbour lists do not: a *learned*, *durability-aware*,
*writer-coupled*, cell-type-transferable map. Honest limits: safety yields risk not certainty and its value is
safe-harbour discrimination; durability is a conditional model with quantified cross-cell-type degradation;
reachability is released at locus level (fine-grained per-site reachability is handled by the Write Planner,
Paper 3); sequence-derived features (ChromBPNet/Borzoi inference) are a deferred enrichment. The atlas is
decision-support, not a clinical directive.

## 5. Data & code availability
Code: https://github.com/ahmedanees-m/pen-stack (MIT, CI-green). Atlas, tracks, models, and feature stores:
Zenodo (CC-BY-4.0), with manifest + SHA-256 checksums. Pre-registration hash: `manuscripts/paper1/prereg_hash.txt`.

## Figures (generated from the released UI + `validation_report.json`)
1. Writability concept + architecture (UI Overview).
2. Safety: safe-harbour vs genotoxic-CIS recovery + baseline gap (UI Validation).
3. Durability: TRIP Spearman/AUROC + feature importance.
4. Writable-genome map + site-finder near a disease gene (UI Forward / Site-finder).
5. Cross-cell-type transfer + comparison to criteria-based GSH lists (UI Cross-cell-type).

## Key references
Akhtar et al. 2013 *Cell* (TRIP) · LaFave et al. 2014 *Nucleic Acids Res.* (MLV integration) · Aznauryan et al.
2022 *Cell Rep. Methods* (Rogi safe harbours) · COSMIC, DepMap, ENCODE, GENCODE, VISDB. Full provenance in
`configs/datasets.yaml`.
