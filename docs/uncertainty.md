# Calibrated uncertainty in PEN-STACK (v3.2)

PEN-STACK is a *trustworthy* co-scientist because every score it returns carries a **calibrated confidence**,
an **extrapolation flag**, and, where the biology is beyond any tool here, an explicit out-of-scope deferral
(see [`scope.md`](scope.md)). This page is the methodology behind the confidence.

The design principle: **wrap, don't retrain.** v3.2 takes the existing Phase-1 LightGBM heads (safety,
durability-silenced classification, durability-expression regression) and turns their point scores into
calibrated intervals/sets; no model is retrained. Small calibration sets yield **wide** intervals; that width
is a real output, reported with N, never hidden.

## Conformal prediction ([`pen_stack/wgenome/uncertainty.py`](../pen_stack/wgenome/uncertainty.py))

- **Regression (durability expression) → prediction intervals.** Split/CV conformal with normalized-residual
  nonconformity; the conformal quantile uses the finite-sample correction `ceil((n+1)(1-α))/n` (returns +∞,
  i.e. "cannot certify", when N is too small to guarantee the coverage). Interval = `ŷ ± q̂·σ`.
- **Classification (safety, silenced) → calibrated prediction sets.** Adaptive Prediction Sets (APS) with an
  optional **Mondrian** (class-conditional) quantile for valid coverage under class imbalance. The set is the
  smallest top-down class set whose cumulative probability reaches `q̂`.
- **Coverage guarantee.** Conformal gives a *distribution-free, finite-sample, marginal* coverage guarantee:
  "the 90% interval covers the truth ≥ 90% of the time." It is **marginal, not conditional**; per-query
  reliability comes from the OOD widening below.

**Results (held-out TRIP, chromosome-grouped split): useful on the expression axis, near-vacuous on the
silenced axis.** The durability **expression** interval covers **0.895** vs a 0.90 nominal (within the
pre-registered ±3-pt tolerance); this axis is where calibrated UQ is genuinely useful. The **silenced**
prediction set covers **0.996** but with **mean size 1.93 of 2**, i.e. it almost always returns the *full*
label set {silenced, not}. Stated plainly: at this N the silenced-axis prediction set is
informative in name only. The conformal *guarantee* holds, but because the head is weak (OOF AUROC 0.64),
APS must emit the full set to certify 90% coverage, so the set carries almost no information. The probabilities
are still well-calibrated (ECE 0.037). This follows the principle that wide intervals from a data-capped signal
are legitimate: report the (near-vacuous) set rather than a tight set the head cannot support.

## Out-of-distribution detection ([`pen_stack/wgenome/ood.py`](../pen_stack/wgenome/ood.py))

A prediction is only as trustworthy as the query's resemblance to the training data. `OODDetector` scores how
far a query sits from the training feature distribution (Mahalanobis / k-NN / isolation-forest) and, when far,
**widens the conformal interval / lowers the confidence** (a monotone widening factor). The threshold is
calibrated on a held-out in-distribution-vs-OOD construction; the separation AUROC is reported.

**What the detector fires on (real data, multiple constructions):**

| Construction | AUROC | Fires? |
|---|---|---|
| chromatin **state** shift, K562 euchromatin → heterochromatin | **0.98** | strongly (the real positive case) |
| cross-cell-type, K562 → HSPC | 0.72 | weakly |
| cross-germ-layer, K562 → HepG2 | 0.65 | weakly |
| cross-**species**, mouse mESC → human K562 (5 shared marks) | **0.56** | barely |

**Key finding (sharpened by the cross-species test).** The detector fires *strongly* when the chromatin
features genuinely move: a euchromatin→heterochromatin state shift separates at **AUROC 0.98** on real K562.
But biological **context** shifts barely move the marginal mark distribution: different cell type (0.65-0.72)
and even **different species** (0.56) are nearly indistinguishable. Histone-mark distributions are remarkably
**conserved across cell types and species** (and per-track normalization compresses them further). So the
extrapolation flag is reliable for **feature-space novelty** (chromatin state, extreme or missing tracks) but
**weak for distinguishing biological context**, itself a useful finding about the limits of
chromatin-mark space for OOD. Reported as a heuristic "far from what I've seen" signal, not a guarantee.

## Selective prediction ([`pen_stack/validate/selective_prediction.py`](../pen_stack/validate/selective_prediction.py))

Uncertainty is only worth reporting if it is *useful*. The **risk-coverage curve** sorts predictions by
confidence and sweeps the retained fraction, abstaining on the least-confident; if the uncertainty is useful,
accuracy rises as coverage shrinks.

**Results:** on the silenced head (held-out TRIP), accuracy rises **0.739 → 0.930** as the least-confident
predictions are abstained (monotone, strictly improving). The model is reliably more accurate on the
predictions it is more confident about, evidence that the uncertainty is actionable, not merely present. Plan-level
confidence (`propagate_plan_confidence`) Monte-Carlos the per-axis intervals into a plan confidence + band,
with OOD widening flipping a plan's epistemic status to *grounded-extrapolating*.

## Off-target & 3D confidence (no overclaim)

The bridge off-target ranker reports a *ranker-calibrated* band (held-out AUROC; **0.88** with the MC3
energetics model, else 0.77) and **abstains** when no genome-wide scan was run, never returning a per-pseudosite
probability the data cannot support. The 3D structural flag abstains when the strong-vs-neutral separation is
within noise; it is a qualitative flag with confidence, never a calibrated probability (no ground-truth
enhancer-hijacking dataset exists to calibrate against).

## What stays out of scope

Coverage is marginal not conditional; intervals are wide because the gold sets are small; OOD flags "far from
what I've seen," not "wrong"; the unknown funnel (structure→phenotype, in-vivo immunogenicity, long-term
clinical durability, higher-order epistasis) stays explicitly out of scope. v3.2 makes that boundary
*legible* ([`scope.md`](scope.md)); it does not close it.
