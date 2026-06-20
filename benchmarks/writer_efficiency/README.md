# Writer-Efficiency Bench

The **first curated, leakage-controlled benchmark for genome-writer integration efficiency**: the track of the
[Genome-Writing Challenge](../genome_writing_challenge/) for *how well a writer writes* (v6.8 PEN-WRITER). Given
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

## Baseline leaderboard (real, on the curated dataset)

| Axis (n) | KB family-mean (MAE / ρ) | **PEN-WRITER learned** (MAE / ρ) | MAE-reduction CI | learned wins? |
|---|---|---|---|---|
| held-out family (42) | 12.72 / −0.20 | **11.37 / +0.52** | [−1.09, 3.75] | no (CI includes 0) |
| held-out locus (35) | 15.23 / −0.26 | **11.71 / +0.38** | [0.42, 6.29] | **yes** (CI excludes 0) |

**Pre-registered outcome:** the learned predictor beats the KB family-mean baseline on
held-out **locus** (CI excludes 0) and **ranks** families far better (ρ +0.52 vs −0.20), but at N=42 across only
**4 families** the held-out-**family** MAE improvement is not statistically distinguishable from zero. So the **KB
ranking is retained as primary**, the learned predictor ships **candidate-flagged**, and the **curated dataset +
this benchmark are the standalone contribution**, not a manufactured win. Reproduce:
`python -c "from benchmarks.writer_efficiency.harness import baseline_leaderboard as b; print(b())"`.

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
  strict subset drops secondary-source rows.
- **Data-thinness**: 4 families is the binding limit; reported, not hidden.

Sources: PASTE (Yarnall *Nat Biotechnol* 2023), (ee)PASSIGE (Pandey/Liu *Nat Biomed Eng* 2025), hyperactive
integrases (Hew *Nucleic Acids Res* 2024), evoCAST (*Science* 2025), ShCAST (Strecker *Science* 2019), enIS621
(*Nat Commun* 2026), ISCro4 (*Science*). Full provenance: [data card](../../docs/cards/writer_efficiency_data.md).
