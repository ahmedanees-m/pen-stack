# Data card: Off-Target-Bench (v6.10 PEN-OFFTGT)

## Summary
A real, leakage-controlled benchmark for cross-writer-family off-target **nomination**: given a guide and its
candidate sites, rank the candidates so the experimentally validated off-targets surface first. Labels are the
wet-lab assay calls (NON-circular: the label is the experiment, not a predictor).

## Ground truth (independently verified 2026-06-19; 4 assays as of v6.10.1)
| Assay | Setting | Guide panel | Citation | DOI |
|---|---|---|---|---|
| GUIDE-seq | cell-based, unbiased | canonical (8) | Tsai et al., *Nat Biotechnol* 2015 | `10.1038/nbt.3117` |
| CIRCLE-seq | in vitro (cell-free), unbiased | canonical (8) | Tsai et al., *Nat Methods* 2017 | `10.1038/nmeth.4278` |
| CHANGE-seq | in vitro, high-throughput | independent broad (20) | Lazzarotto et al., *Nat Biotechnol* 2020 | `10.1038/s41587-020-0555-7` |
| SITE-seq | in vitro biochemical | independent broad (11) | Cameron et al., *Nat Methods* 2017 | `10.1038/nmeth.4284` |

Canonical Cas9 guides: **EMX1, VEGFA site 1/2/3, FANCF, HEK293 site 2/3/4**. CHANGE/SITE-seq use **independent broad
guide panels** (not the canonical 8), a cross-assay generalization test. The harmonized candidate/label tables are
sourced from the CRISOT data release (Zenodo `10.5281/zenodo.8420032`), which redistributes the public assay
supplements; PEN-STACK cites the **original assay papers** as the ground-truth provenance.

## Learned predictor (real tool, VM-only)
**CRISOT-Score** (Chen et al., *Nat Commun* 2023, `10.1038/s41467-023-42695-4`): an XGBoost RNA-DNA interaction
fingerprint. **License: CC-BY-NC** → it runs only on the VM (`crisot:tools` Docker, `xgboost`/`pandas`/`numpy`);
its weights are NEVER redistributed. Only DERIVED scores are cached/committed (CI-safe), exactly like the licensed
NetMHC tools.

## Baseline (pre-registered)
Sequence-homology nomination = ascending **mismatch count** (Hamming over the 20-nt protospacer).

## Result (full real data, on the VM)
CRISOT-Score is the MD-physics, **assay-agnostic** scorer (not fit on these labels) → a leakage-clean held-out
evaluation on every assay.

| Assay | guide panel | CRISOT AUPRC | homology AUPRC | gap | 95% CI (held-out-guide bootstrap) | beats |
|---|---|---|---|---|---|---|
| GUIDE-seq | canonical (8) | 0.646 | 0.467 | +0.179 | [0.014, 0.329] | yes |
| CIRCLE-seq | canonical (8) | 0.520 | 0.266 | +0.253 | [0.146, 0.370] | yes |
| CHANGE-seq | independent (20) | 0.541 | 0.249 | +0.292 | [0.235, 0.348] | yes |
| SITE-seq | independent (11) | 0.521 | 0.233 | +0.287 | [0.239, 0.335] | yes |

The learned predictor beats the homology baseline on **all four** assays (per-guide bootstrap CI excludes 0),
including two independent broad guide panels (cross-assay generalization).

## Chromatin-accessibility modifier: VALIDATED (moderate, cell-type-matched)
The nominator applies a documented chromatin modifier (open chromatin raises realized off-target activity;
Lazzarotto 2020). It reads the **real accessibility track** (`phase_1/features/chromatin_{ct}.parquet`,
ATAC/DNase) when a candidate's genomic locus + cell type are supplied AND the feature store is present (verified on
the VM), or accepts a caller-supplied scalar; it **abstains** otherwise (the bare wheel / CI / deployed atlas do not
ship the raw track).

**Controlled validation** (`benchmarks/offtarget/chromatin_validation.json`): off-targets mapped to hg38 (98.5%),
AUROC of accessibility for active-vs-inactive off-targets per assay, with in-vitro assays as a NEGATIVE control.

| Assay | modality | AUROC (K562 cross-cell) | **AUROC (HEK293T matched)** | 95% CI (matched) |
|---|---|---|---|---|
| GUIDE-seq | cell-based (WT Cas9) | 0.58 | **0.671** ↑ | [0.642, 0.701] |
| TTISS | cell-based (Cas9 *variants*) | 0.346 | 0.383 (outlier) | [0.362, 0.405] |
| SITE-seq | in-vitro control | 0.469 | 0.494 (null) | [0.475, 0.514] |

**v6.10.2** used a cross-cell K562 proxy → weak/inconsistent. **v6.10.3** used a CELL-TYPE-MATCHED ENCODE HEK293T
DNase track (`ENCFF529BOG`, matching GUIDE-seq's HEK293 and TTISS's HEK293T): **cell-type matching lifts the
canonical WT-Cas9 cell-based assay from 0.58 → 0.671** (the cross-cell proxy was dampening a real effect), with the
in-vitro control still null. **Verdict: VALIDATED (moderate, cell-type-matched)** for WT-Cas9 cell-based off-target
activity. Caveats: the effect is **moderate** (the sequence/CRISOT score dominates nomination); it does
**not** transfer to TTISS (a Cas9-variant specificity assay, the expected outlier).

**Incremental value over CRISOT (v6.10.4, `chromatin_incremental.json`):** on GUIDE-seq (HEK293T-matched),
accessibility carries a **small real conditional signal** (logistic-regression coefficient ~0.35, bootstrap CI
excludes 0 at both 1:16 and 1:123 candidate imbalance) but adds **NO held-out ranking improvement** over CRISOT
(leave-one-guide-out AUPRC gap CI includes 0 at both). **Decision: chromatin is a validated ANNOTATION, NOT a
re-ranker**: it does **not** change the numeric risk score (CRISOT already captures the practically-relevant ranking
signal); the fitted CRISOT+accessibility combiner is recorded but intentionally not applied. Reproducible:
`scripts/offtarget_chromatin_{validation,matched,incremental}.py`.

## Risk calibration (grounded)
The nomination risk band IS the empirical fraction of candidates at *k* mismatches that were validated-active
(full real data): GUIDE-seq 0-1 mm → 1.00, 2 mm → 0.765, 3 mm → 0.231, 4 mm → 0.033, 5 mm → 0.0028, 6 mm → 0.00014.
Mismatch counts outside the calibrated range abstain rather than extrapolate.

## Files
- `benchmarks/offtarget/offtarget_bench_fixture.csv`: real validated off-targets + cached CRISOT scores (CI-safe;
  inactives downsampled with a fixed seed for a small committed file).
- `benchmarks/offtarget/offtarget_bench_metrics.json`: the AUTHORITATIVE full-data metrics.
- `benchmarks/offtarget/offtarget_calibration.json`: the full-data mismatch / CRISOT-decile calibration.
- `benchmarks/offtarget/split.json`, `SHA256SUMS`: split definition + checksums.

## Limitations
Nomination is **not** a clearance; every result ships with the empirical assay that would confirm it. Genome-wide
candidate ENUMERATION needs the on-VM Cas-OFFinder/genome scan; this benchmark covers SCORING + RANKING of supplied
candidates. Bridge/integrase off-target is data-thin: there is **no published genome-wide unbiased off-target assay
or predictor for bridge recombinases** (verified), and the large-serine-integrase assays (Cryptic-seq/HIDE-seq) and
predictor (IntQuery) are recent single-company preprints with no public weights.

---

## v7.2 (PEN-OFFTGT v2) — per-mechanism ground-truth status (O-WS8 / gate O-G3)

Stage E is now a genome-wide **finder** (Cas-OFFinder over GRCh38; heavy scan on the VM, cached coordinates
replayed by the app). Each writer class applies the correct off-target mechanism and carries a **truthful
validation status** — a sealed benchmark where ground truth exists, an explicit **no-genome-wide-ground-truth
disclosure** where it does not. No mechanism is ever presented as validated where the data cannot support it.

| Writer class | Mechanism | Enumeration | Status | Ground truth / benchmark |
|---|---|---|---|---|
| **Nuclease** (SpCas9/SaCas9/Cas12a) | mismatch-tolerant cleavage at protospacer+PAM | Cas-OFFinder genome scan | ✅ **validated** | 4-assay Off-Target-Bench (above) + **O-G1**: enumeration recovers 100% of EMX1's documented GUIDE-seq off-targets ≤5 mm |
| **Serine integrase** (Bxb1) | recombination at genomic pseudo-attP | fixed-sequence att-window scan | 🟡 **semi-validated** | documented pseudosites are partial ground truth; Bxb1 att verified (FlyBase FBto0000359 / Ghosh 2003, `10.1016/S1097-2765(03)00444-1`); Bxb1 is highly specific (few genomic pseudo-attP) |
| **Serine integrase** (PhiC31) | — | — | 🟡 semi-validated | **DISCLOSED DATA GAP**: PhiC31 has ~19 documented human pseudo-attP (Chalberg 2006, `10.1016/j.jmb.2005.11.108`) — the strongest integrase benchmark — but its exact att arm / pseudosite sequences were not verifiable from an open source in this build, so PhiC31 is **not encoded and abstains** rather than fabricate. Encoding it is the follow-up that upgrades O-G2 to a sealed recall benchmark. |
| **Bridge** (IS110/IS621) | recombination at bridge-RNA target-loop matches | core-seeded genome scan (pysam) | 🔵 **mechanism-based, unvalidated** | **NO genome-wide unbiased CELLULAR off-target assay exists** (technology ~2024). The mismatch-tolerance RANKER is validated on the measured Perry-2025 in-vitro DMS specificity (held-out ranking AUROC 0.88), but genomic recovery is unvalidated. |
| **CAST** (ShCAST V-K / VchCAST I-F) | guide-directed integration + guide-independent untargeted transposition | spacer scan + per-system untargeted background | 🔵 **mechanism-based, unvalidated** | untargeted-transposition rates documented per system (`data/curated/cast_systems.yaml`): ShCAST high/AT-biased (Strecker 2019 `10.1126/science.aax9181`; Science 2024 `10.1126/science.adj8543`), VchCAST >95–99% on-target (Klompe 2019 `10.1038/s41586-019-1323-z`; Vo 2021 `10.1038/s41587-020-00745-y`). No genome-wide cellular assay for human-cell CAST. |
| **PASTE / (ee)PASSIGE** | Cas9-nickase off-target + integrase pseudo-attP | compose(nuclease, integrase) | composite (✅ nickase + 🟡 integrase) | inherits the nuclease benchmark for the nickase and the integrase status for the installed att; recommends BOTH a nuclease assay AND an integrase assay |

**O-G3 satisfied:** every mechanism has either a sealed benchmark (nuclease) or an explicit no-ground-truth /
data-gap disclosure (integrase-PhiC31, bridge, CAST) — never a fabricated metric. The bridge and CAST paths are
**hard-locked** to 🔵 unvalidated in code.

**Honest limits (v7.2):** enumeration recall depends on the mismatch tolerance (≤5 mm nuclease, ≤8 mm integrase
att window); very divergent off-targets can be missed (a limitation shared with CRISPOR). DNA/RNA bulges are not
enumerated in v2.0 (substitutions only). The engine nominates and ranks; it does not clear a design.
