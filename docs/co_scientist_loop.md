# The co-scientist over the loop

The matured co-scientist drives the whole loop for a working scientist: every output safe, legal,
calibrated, cited, scope-ledgered, and **immune-profiled**, and never fabricated. **The co-scientist drives and
presents; the scientist/lab decides.**

```python
from pen_stack.agent.co_scientist import co_scientist_session
session = co_scientist_session(goal, cell_state="k562")
```

Returns, for a documented goal:

| Key | From | What |
|---|---|---|
| `strategies` | - | the Pareto frontier of designs (incl. the grounded immune-risk axis) |
| `predicted_outcomes` | - | calibrated outcomes with intervals + scope flags |
| `immune_profiles` | - | the per-axis immune-risk vector, **first-class** (`collapsed_score is None`) |
| `suggested_experiments` | - | the diverse, informative batch to run next (EIG + immune-VOI) |
| `protocols_available` | - | safety-gated protocol export on request (DRAFT) |
| `citations` | - | a literature-cited rationale (citations resolve by construction) |
| `scope_ledger` | - | what was assessed vs not (the known-unknowns made legible) |
| `safety` | - | the per-design safety decision (cleared / flagged) |

Hazardous candidates are discarded by the safety-gated pipeline before they ever appear. No number is
fabricated; the immune-risk profile is presented **with its known-unknowns**, never as a patient prediction.

## Scope

The co-scientist runs the loop and **presents options**; it does not decide. Safety, no-fabrication, calibration,
and the scope ledger hold throughout. It is the most useful *face* of the substrate, not an autonomous agent.
