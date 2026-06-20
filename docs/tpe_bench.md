# TPE-Bench: the position-effect / expression benchmark (v6.7)

The **expression** capability never had a held-out benchmark. TPE-Bench fills that gap as a track of the
[Genome-Writing Challenge](../benchmarks/genome_writing_challenge/): given a genomic **chromatin context** +
**cassette**, predict the **integrated-reporter expression** (and silencing), scored on a **sealed** split.

Location: `benchmarks/position_effect/` (`harness.py`, `split.json`, `SHA256SUMS`, `README.md`).

## Two tracks

| Track | Status | Held out | Metric |
|---|---|---|---|
| `chrom_holdout` | **LIVE** | whole chromosomes `chr2, chr5, chr14, chrX` (frozen + SHA-locked) | Spearman ρ + AUROC |
| `celltype_holdout` | **DATA-GATED** | leave-one-cell-type-out (the primary transfer test) | not yet scored |

`celltype_holdout` is the cross-cell-type transfer test. With one available position-effect cell type (mESC) it
returns `data_gated` and activates once PatchMPRA / MPIRE / lentiMPRA / Leemans are fetched. **No
transfer number is fabricated.**

## Baseline leaderboard (`chrom_holdout`, sealed, n_test = 2257)

| Predictor | Expression ρ | Silenced AUROC |
|---|---|---|
| cassette-only | 0.178 | n/a |
| context-only (v3.x durability head) | 0.431 | 0.660 |
| **PEN-EXPRESS factored** | **0.475** | 0.660 |

The factored model's gain is on **expression** (ρ 0.431 → 0.475 on the sealed held-out chromosomes); the silencing
classifier matches the durability head (chromatin-driven), reported as measured rather than inflated.

## Discipline

- **Sealed + SHA-locked.** `split.json` is frozen and checksummed (`SHA256SUMS`) **before model selection**;
  verify with `sha256sum -c benchmarks/position_effect/SHA256SUMS`.
- **Non-circular labels.** The label is the **measured** TRIP expression, never a submitter claim.
- **Leakage-controlled.** Held out by whole chromosome (nearby integrations share chromatin).
- **Data-gating.** The transfer track abstains until ≥2 cell types exist.

## Submit

```python
from benchmarks.position_effect.harness import Submission, evaluate
def predict(pi):  # pi = {task_id, cassette, chromatin_features, instructions}; label hidden
    return {"expression": 0.0, "p_silenced": 0.5}
print(evaluate(Submission("my-model", predict)))
```

Reproduce the baselines: `python -c "from benchmarks.position_effect.harness import baseline_leaderboard as b; print(b())"`.
