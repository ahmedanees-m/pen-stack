# The digital twin (v5.9)

From v5.9, PEN-STACK can predict *what the cell does after the write*: calibrated, OOD-gated, and scope-bounded.
It computes what mechanism allows, adds an in-distribution virtual-cell estimate, screens immune outcome from the
v5.6 profile, and states its boundary at phenotype plainly. The twin is a **hypothesis engine, not an oracle of
truth**.

```python
from pen_stack.twin import predict_outcome
o = predict_outcome(design, cell_state="k562")
o["predicted_outcome"]   # {relative_expression, vcell_response, units}
o["interval"]            # heuristic band; WIDENS under OOD
o["immune_outcome"]      # the v5.6 per-axis profile (sourced, not invented)
o["scope_flags"]         # phenotype_not_modeled, in_vivo_magnitude_unknown, (vcell_OOD if extrapolating)
```

## Mechanism where computable (`pen_stack/twin/mechanistic.py`)

`cassette_expression(design, chromatin_ctx)` = `promoter_strength × copy_number × accessibility`, a closed-form
steady-state estimate. Assumptions (steady-state, no silencing, linear copy scaling) and scope flags
(`episomal_durability_unknown`, `phenotype_not_modeled`) travel with the output. It is **physics where
computable, never a phenotype**.

## Virtual-cell oracle, OOD-gated (`pen_stack/oracles/vcell.py`)

`predict_response(cell_state, perturbation, model="state")` wraps Arc **STATE** / **scGPT** under the v4.0
`OracleResult` contract. A perturbation-response prediction is a **candidate**, never a claim; a cell context or
perturbation outside the documented validity envelope sets `extrapolating=True` / `in_scope=False`. The backend is
deferred/cache-replayed (value `None` when absent, never fabricated). This encodes the field's own result (Arc's
Virtual Cell Challenge): **perturbation models do not yet consistently beat naive baselines** and do not
generalize to unseen contexts.

## Fused outcome (`pen_stack/twin/outcome.py`)

`predict_outcome(design, cell_state)` fuses the computable mechanistic estimate (backbone) + an in-distribution
virtual-cell response (when available) + the v5.6 immune profile. The interval **widens under OOD** rather than
over-trusting an extrapolating model. For in-vivo vehicles, durability **may be conditioned on the grounded
pre-existing-NAb axis** (no invented immune numbers). Phenotype and in-vivo magnitude stay scope-flagged.

> The interval is a heuristic band, **not** a trained conformal interval: there is no public
> perturbation-outcome calibration set. The twin says so.

## Calibration (`pen_stack/twin/calibrate.py`)

`calibrate_outcome(predictions, observations, intervals=…)` reports calibration **two-sided, whatever the shape**:
interval coverage vs nominal, and a skill comparison against a naive mean baseline with a **bootstrap CI on the
MAE gap**. The twin "beats" the baseline **only when the CI excludes zero**; otherwise the negative is reported
verbatim. At `N < 3` it abstains.

## Scope

The twin predicts what mechanism computes, what an in-distribution virtual-cell model supports, and what the v5.6
immune profile screens, with calibrated intervals. It does **not** predict phenotype, in-vivo behaviour,
immunogenicity *magnitude*, or durability beyond the computable; these stay scope-flagged. Perturbation prediction
is an open problem; the twin is a calibrated hypothesis engine, with its weak points stated plainly.
