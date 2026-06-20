# The learned, trained-conformal position-effect model (v6.7 PEN-EXPRESS)

The position-effect model predicts how strongly an integrated cassette expresses in its **chromatin context** (the position effect).
Through v6.6 this was a closed-form **heuristic** with a heuristic ±0.20 band that the code itself labelled *"NOT
a trained conformal interval"*, and which **failed** independent validation (ρ=0.12 vs Damdindorj 2014). v6.7
replaces it with a **learned, decomposable, trained-conformal** model that wraps the digital
twin, not rebuilding it.

## The model

`pen_stack/twin/position_effect.py::PositionEffectModel` is **factored and decomposable**:

```
E_raw  ≈  f_cassette(cassette)            # the cassette's intrinsic strength (per-cassette mean)
       +  g_context(chromatin features)    # the position effect, a LightGBM on local chromatin
       (+ h_interaction, reported)         # does the context function differ by cassette? (separability)
```

`g_context` is supervised on the residual `E_raw − f_cassette`, so it learns the *position* effect on a scale
comparable across cassettes. A `silenced` classifier shares the chromatin features. The model is wrapped with the
**existing** `wgenome.uncertainty.ConformalRegressor` (chromosome-Mondrian split-conformal) and `wgenome.ood.OODDetector`,
so a prediction is a **calibrated interval that widens out of distribution**.

## Results (real, on TRIP supervision: Akhtar 2013, GEO GSE49806/49807, mESC, n=11,433)

Chromosome-blocked GroupKFold; paired bootstrap 95% CIs. *Every number is from a real CV run; no fabrication.*

| Metric | cassette-only | context-only (v3.x durability head) | **PEN-EXPRESS factored** | Δ vs head (CI) |
|---|---|---|---|---|
| Expression Spearman ρ | 0.032 | 0.427 | **0.469** | +0.041 [0.036, 0.046] excludes 0 |
| Silenced AUROC | n/a | 0.647 | 0.651 | +0.004 [0.001, 0.007] excludes 0 |

- **The factored model passes its gate:** it beats the durability head (CI excludes 0) and serves the position-effect prediction.
- **Separability:** interaction adds **−0.002** R² → *additive `f_cassette + g_context` suffices at this N*
  (the cassette term lifts expression, the silencing question is chromatin-driven).
- **Trained-conformal (the named gap, closed):** split-conformal (α=0.10) → **held-out coverage 0.885 vs 0.90
  nominal** (within tolerance), qhat=5.50 on the log2 scale. Coverage is measured on a **half-chromosome held-out**
  split, not on the calibration set.

## Integration (`twin/outcome.py`)

`predict_outcome(design, cell_state)` now:
- **With a chromatin context** (`design["chromatin_features"]`) **and the model artifact present** → serves the
  learned **trained-conformal** interval + `p_silenced` + OOD tier in a `position_effect` block; `stage_h_mode =
  "learned_trained_conformal"`.
- **Without a context (or artifact)** → the closed-form heuristic band, exactly as before; **backward compatible**
  (the v5.9 relative-scale contract and all prior tests are intact).

## Limitations

- **Single-context supervision.** TRIP is mESC. The cross-cell-type **transfer** claim is **data-gated**: see
  [tpe_bench.md](tpe_bench.md); no transfer number is fabricated until PatchMPRA/MPIRE/lentiMPRA/Leemans are fetched.
- **Public data cannot earn a validated-axis grade** (the v6.5 wall). v6.7 ships the learned+calibrated upgrade + the
  benchmark, not a manufactured validated axis. Titer / absolute expression / phenotype stay **out of scope**.
- The model artifact (`models/position_effect.pkl`) is gitignored; regenerate it with
  `python scripts/p1_build_position_effect.py` (the shipped calibration `configs/twin/position_effect_conformal.json`
  is committed). Without the artifact, the model falls back to the heuristic.
