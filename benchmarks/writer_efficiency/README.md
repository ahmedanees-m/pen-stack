# Writer-Efficiency Bench

The **first curated, leakage-controlled benchmark for genome-writer integration efficiency**: the track of the
[Genome-Writing Challenge](../genome_writing_challenge/) for *how well a writer writes*. Given
`(family, write-type, cargo, locus, cell-type, variant)`, predict the **integration efficiency (%)**, scored on
**held-out family** and **held-out locus** folds.

## Why

Quantitative human-cell writer efficiencies exist but are **scattered** across a dozen papers with no unified
resource. This bench curates them (`data/writer_efficiency.parquet`, ~45 records, **every row carries a DOI + a
verbatim source quote + a source-access grade**) so others can build a calibrated efficiency predictor *to* it.

## Tracks (both leakage-controlled, leave-one-group-out)

| Axis | Held out | Why |
|---|---|---|
| `held_out_family` | one of {PE_integrase, serine_integrase, bridge_IS110, CAST_VK} | cross-family transfer, the hard axis |
| `held_out_locus` | one specific locus (excludes aggregate/genome-wide pseudo-loci) | locus-context generalisation |
| `held_out_study` | one source paper | a row cannot be predicted from other rows of the same paper |

## Baseline leaderboard (real, on the curated dataset)

| Axis (n) | KB family-mean (MAE / ρ) | **learned model** (MAE / ρ) | MAE-reduction CI | learned wins? |
|---|---|---|---|---|
| held-out family (42) | 12.72 / −0.20 | **11.37 / +0.52** | [−1.09, 3.75] | no (CI includes 0) |
| held-out locus (35) | 15.23 / −0.26 | **11.71 / +0.38** | [0.42, 6.29] | **yes** (CI excludes 0) |

**Pre-specified outcome:** the learned predictor beats the KB family-mean baseline on
held-out **locus** (CI excludes 0) and **ranks** families far better (ρ +0.52 vs −0.20), but at N=42 across only
**4 families** the held-out-**family** MAE improvement is not statistically distinguishable from zero. So the **KB
ranking is retained as primary**, the learned predictor ships **candidate-flagged**, and the **curated dataset +
this benchmark are the standalone contribution**, not a manufactured win. Reproduce:
`python -c "from benchmarks.writer_efficiency.harness import baseline_leaderboard as b; print(b())"`.

## Source provenance against writer family

Source-access grade and writer family are **not separable** in this table. All six records that are not
`pmc_verbatim` belong to `bridge_IS110`, and that family carries no `pmc_verbatim` record, so restricting the
table by source grade and removing a family are close to the same operation. `strict=True` is a high-confidence
subset, not a provenance control: it leaves `bridge_IS110` a single record and the cross-family fold degenerate.

| Family | `pmc_verbatim` | `abstract` | `secondary` |
|---|---|---|---|
| PE_integrase | 23 | 0 | 0 |
| serine_integrase | 11 | 0 | 0 |
| CAST_VK | 5 | 0 | 0 |
| bridge_IS110 | **0** | 1 | 5 |

Two consequences carry into the evaluation, both in `provenance_sensitivity.json`:

- **The held-out-locus axis carries no non-primary record.** Every non-primary human record sits at an aggregate
  pseudo-locus (`endogenous_avg`, `best_locus`, `human_genome`) that the specific-locus mask already excludes, so
  the axis on which the learned model wins rests wholly on primary-source rows and is identical on every
  source-grade basis.
- **The cross-family outcome does not rest on source grade.** It spans zero on the full table and on the three
  families carrying full primary-source provenance.

| Basis (n, families) | held-out family | held-out locus | held-out study |
|---|---|---|---|
| full (42, 4) | [−1.09, 3.75] | [0.42, 6.29] | [1.30, 6.93] |
| `pmc_verbatim` only (37, 3) | [−2.28, 3.42] | [0.42, 6.29] | [0.07, 6.37] |
| `pmc_verbatim` + `abstract` (38, 4) | [−4.86, 1.49] | [0.42, 6.29] | [1.75, 7.25] |

95% paired-bootstrap interval on the MAE reduction over the KB family-mean baseline. The runner reproduces the
released `result.json` metrics exactly before it reports any subset, and withholds the subset metrics otherwise.
Regenerate: `python benchmarks/writer_efficiency/provenance_sensitivity.py`.

The four `secondary` human-cell figures match their primary texts: 6.82% and 14.76% are the enIS621-tebRNA
averages over AAVS1 site3 and B2M intron 1 in HEK293T and in Jurkat T cells; insertion above 6% is the ISCro4
figure in Pelea et al.; up to 20% with 82% specificity is the engineered ISCro4 figure in Perry et al. The 27.75%
figure appears in the enIS621 abstract and nowhere in that paper's results or methods, which is the grade the row
carries.

## Submit

```python
from benchmarks.writer_efficiency.harness import Submission, evaluate
def predict(pi):  # pi = {family, write_type, variant, cargo_bp, locus, cell_type, delivery}; label hidden
    return {"efficiency_pct": 15.0}
print(evaluate(Submission("my-model", predict)))
```

## Discipline

- **Sealed + SHA-locked**: `split.json` + `data/writer_efficiency.parquet` are checksummed in `SHA256SUMS`.
- **Non-circular**: the label is the **measured published efficiency**, never a submitter claim.
- **Provenance per row**: DOI + verbatim quote + `source_access` ∈ {pmc_verbatim, abstract, secondary}; the
  strict subset drops secondary-source rows, which also removes a family, so read it as a confidence subset and
  not as a provenance control.
- **Data-thinness**: 4 families is the binding limit; reported, not hidden.

Sources: PASTE (Yarnall *Nat Biotechnol* 2023), (ee)PASSIGE (Pandey/Liu *Nat Biomed Eng* 2025), hyperactive
integrases (Hew *Nucleic Acids Res* 2024), evoCAST (*Science* 2025), ShCAST (Strecker *Science* 2019), enIS621
(*Nat Commun* 2026), ISCro4 (*Science*). Full provenance: [data card](../../docs/cards/writer_efficiency_data.md).
