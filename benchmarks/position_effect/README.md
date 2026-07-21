# TPE-Bench: the Position-Effect / Expression track

The **expression** capability of PEN-STACK never had a held-out benchmark. TPE-Bench is the position-effect
track for the [Genome-Writing Challenge](../genome_writing_challenge/): given a genomic
**chromatin context** + **cassette**, predict the **integrated-reporter expression** (and silencing), scored on
a **sealed held-out split** whose labels the submitter never sees.

## Why

Position-effect (where an integrated cassette lands → how strongly/durably it expresses) is the writing-relevant
quantity no safe-harbour resource predicts. TRIP (Akhtar 2013) supervises it directly. TPE-Bench seals a held-out
split and anchors a baseline leaderboard, so others can build *to* a calibrated expression predictor.

## Tracks

| Track | Status | What is held out | Metric |
|---|---|---|---|
| `chrom_holdout` | **LIVE** | whole chromosomes (`chr2, chr5, chr14, chrX`), frozen + SHA-locked in `split.json` | Spearman ρ (expression) + AUROC (silenced) |
| `celltype_holdout` | **ACTIVATED** (see note) | leave-one-cell-type-out (the primary transfer track) | Spearman ρ (expression) |

`celltype_holdout` is the primary cross-cell-type transfer test. With a single available position-effect cell
type (mESC) it reported `data_gated`, and activated once the human data was acquired: **no transfer number is
fabricated** until then.

> **Update (release of record).** The **Leemans 2019 K562 TRIP** data has since been acquired and a
> human K562 position-effect head trained and evaluated on a fresh sealed held-out split. That result - the
> human companion to this benchmark - lives in [`../position_effect_human/`](../position_effect_human/)
> (held-out ρ = 0.571; circularity-guarded independent variant ρ = 0.558; cross-cell-type/resolution matrix).
> The sealed `split.json` above intentionally still records `data_gated`: it is a **frozen, SHA-locked** record
> of the split's state at sealing and is not re-cut (per the no-broken-trail policy); the current status is
> tracked here and in `position_effect_human/`, not by editing the sealed file.

## Baseline leaderboard (sealed `chrom_holdout`, n_test = 2257)

| Predictor | Expression ρ | Silenced AUROC |
|---|---|---|
| cassette-only (f_cassette) | 0.178 | n/a |
| context-only (durability head) | 0.431 | 0.660 |
| **Factored (f_cassette + g_context)** | **0.475** | 0.660 |

The factored model's gain is on **expression** (the cassette term lifts ρ 0.431 → 0.475 on the sealed test); the
silenced classifier matches the durability head (the silencing question is chromatin-driven, reported as measured,
not inflated). See `../../out/position_effect_report.json` for the full CV report + bootstrap CIs.

## How to submit

```python
from benchmarks.position_effect.harness import Submission, evaluate

def my_predict(public_input: dict):
    # public_input = {task_id, family, cassette, chromatin_features:{H3K27ac,...}, instructions}; label hidden
    return {"expression": 0.0, "p_silenced": 0.5}   # return your prediction (abstain-safe)

print(evaluate(Submission(name="my-model", predict_fn=my_predict)))
```

Reference baselines: `python -c "from benchmarks.position_effect.harness import baseline_leaderboard as b; print(b())"`.

## Rules

- **Sealed + SHA-locked.** `split.json` (held-out chromosomes) is frozen and checksummed (`SHA256SUMS`) before
  model selection; verify with `sha256sum -c SHA256SUMS`.
- **No circular labels.** The label is the **measured** TRIP expression, never a submitter claim.
- **Leakage-controlled.** Held out by whole chromosome (nearby integrations share chromatin).
- **Data-gating.** The transfer track abstains until ≥2 cell types exist; no fabricated number.
- **Deterministic.** The factored model anchors the leaderboard.

Data: TRIP (Akhtar et al., *Cell* 2013; GEO GSE49806/GSE49807; trip.nki.nl). License: see `DATA_LICENSES.md`.
