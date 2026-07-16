# The experiment designer (v5.10)

From v5.10, PEN-STACK turns *"I'm uncertain"* into *"run **this** experiment next."* It reads the calibrated v5.9
twin's uncertainty and the v5.6 immune-risk labels, scores each candidate experiment by the information it is
expected to yield, assembles a diverse batch, and proves on held-out data, with confidence intervals, that this
learns faster than random or greedy, reporting plainly when it does not. The **Learn** brain of a self-driving
lab: lab-optional and falsifiable by construction.

## Acquisition (`pen_stack/active/acquire.py`)

```python
from pen_stack.active import acquisition_score, expected_information_gain, immune_voi
```

- **`predictive_entropy(outcome)`**: the twin's current uncertainty, from its interval width (Gaussian
  differential entropy).
- **`expected_information_gain(candidate, cell_state)`**: reducible uncertainty: `entropy now − expected
  posterior entropy` (a measurement collapses the predictive sd toward a noise floor); `≥ 0`. Monotone in the
  twin's uncertainty (an OOD candidate yields more EIG).
- **`immune_voi(candidate)`**: value of information for **validating an immune PROXY axis** (v5.6): an axis still
  labelled a proxy that this experiment would measure is high-VOI (it would turn proxy → outcome-validated).
- **`acquisition_score`** = `w_eig·EIG + w_unc·entropy + w_imm·immune_voi`. Fully traceable to twin quantities +
  v5.6 labels; deterministic given inputs (no fabricated values).

## Diverse batch (`pen_stack/active/design.py`)

`select_batch(candidates, cell_state, k)` greedily maximises summed acquisition **minus a redundancy penalty**
(shared design facets) against the already-chosen set, so a batch is a *diverse* set of informative experiments,
not k copies of the single most-uncertain point. Each chosen experiment carries its `expected_info_gain`.

## Retrospective falsifiability (`pen_stack/active/validate.py`)

`retrospective_active_learning(dataset, strategies=("active","random","greedy"))` simulates campaigns per
strategy on a held-out split, records the held-out-MAE learning curve per round, and over repetitions reports
mean±CI curves and a **bootstrap CI on the curve-area gap** (`random_area − active_area`). The active learner
"beats" random **only when the CI excludes zero**; otherwise the not-yet-useful negative is reported verbatim, a
valid, published outcome.

## Scope

The experiment designer is only as good as the v5.9 twin and the v5.6 labels it queries. Its advantage is
validated **retrospectively** on existing data with confidence intervals, and reported plainly when absent. It
chooses informative experiments, including ones that would validate an immune proxy, but it **does not run
them**; prospective benefit awaits a lab partner (v5.11+).
