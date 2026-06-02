# Score my construct for AAV deliverability

**Goal:** decide whether a writer effector fits in a single AAV, needs split-AAV, or must be delivered
as mRNA-RNP — and read its full therapeutic-readiness profile.

Deliverability is a function of effector size (a single AAV packages roughly a ≤4.7 kb payload, i.e. a
≤~730 aa effector). Thresholds live in `configs/score_axes.yaml` (no per-enzyme overrides).

## Python

```python
from pen_stack.score.therapeutic import deliverability_class, therapeutic_profile
from pen_stack.score.recalibrate import load_axes_config
import pandas as pd

cfg = load_axes_config()
print(deliverability_class(326, cfg))   # ISCro4 -> 'AAV'
print(deliverability_class(1368, cfg))  # SpCas9 -> 'split-AAV'

atlas = pd.read_parquet("pen_stack/atlas/atlas.parquet")
prof = therapeutic_profile(atlas)
print(prof[prof.representative_system == "ISCro4"]
      [["deliv_class", "S_Deliv", "S_Cargo", "S_HumanCell", "readiness"]])
```

## Classes

| Class | Effector size | S_Deliv |
|---|---|---|
| `AAV` | ≤ 730 aa | 1.0 |
| `split-AAV` | ≤ 1500 aa | 0.6 |
| `mRNA-RNP` | > 1500 aa | 0.4 |

The `readiness` score is the mean of available components (`S_Deliv`, `S_Cargo`, `S_HumanCell`,
`S_DSBfree`) — **always inspect the components**, never just the composite. Cargo design (insulation,
promoter, polyA) is a separate, composable factor handled by the Write Planner.
