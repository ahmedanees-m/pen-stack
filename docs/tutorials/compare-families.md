# Compare CAST vs bridge vs PASTE vs integrase

**Goal:** compare writer families on common, *measured* axes to pick the right modality for an insertion.

The Writer Atlas places every family on the same axes with explicit confidence + provenance.

## Python

```python
import pandas as pd
atlas = pd.read_parquet("pen_stack/atlas/atlas.parquet")
core = atlas[atlas.entry_kind == "curated_core"]
print(core[["representative_system", "family", "mechanism_bucket", "targeting_modality",
            "cargo_capacity_bp", "deliv_class", "reachability_tier", "readiness"]])
```

## CLI

```bash
pen-stack atlas --coverage
```

```
          family     n  measured                    tier
         CAST_VK   264         1 Tier2_context_candidate
    bridge_IS110 31885         2         Tier1_scannable
    PE_integrase     1         1         Tier1_scannable
serine_integrase  1036         2 Tier2_context_candidate
 ...
TOTAL systems: 33,370 across 8 families
```

## At a glance

| Family | Cargo | DSB-free | Reachability | Deliverability | Human-cell |
|---|---|---|---|---|---|
| **bridge_IS110** (ISCro4) | ~5 kb intrinsic | yes | Tier 1 (scannable core) | AAV (326 aa) | measured (~20% ins) |
| **CAST_VK** (ShCAST) | ~10 kb | yes | Tier 2 (PAM + fixed distance) | mRNA-RNP | low in human |
| **serine integrase** (Bxb1) | ~50 kb | yes | Tier 2 (pseudo-att) / Tier 1 if att installed | mRNA-RNP | high at installed att |
| **PE_integrase** (PASTE) | ~36 kb | yes | Tier 1 (PE-installable att) | mRNA-RNP | human cells, primary T, hepatocytes |

Every value carries a confidence tag (`measured` / `inferred` / `predicted`) and a source DOI. Use the
**Writer Atlas** page of the Streamlit UI to compare readiness interactively.
