# Where can I write X in cell type Y?

**Goal:** find safe, durable insertion loci near a target gene, in a specific cell type.

The Writable Genome scores every 1 kb bin for `writability = safety × durability`, learned blind on
public data (COSMIC/DepMap + 3.7M MLV integration sites for safety; TRIP position effects for
durability). It is *conditional on the supplied epigenome*, so the cell type matters.

## CLI

```bash
pen-stack writable --gene CCR5 --ct k562 --top 10
```

```
chrom    bin  safety  p_durable  writability
 chr3  46364     1.00      0.92         0.918
 ...
```

## Python

```python
from pen_stack.atlas.crosslink import loci_for_gene

loci = loci_for_gene("CCR5", ct="k562")
best = loci.sort_values("writability", ascending=False).head(10)
print(best[["chrom", "bin", "safety", "p_durable", "writability"]])
```

## REST

```bash
curl 'http://localhost:8000/writable?gene=CCR5&ct=k562&top=10'
```

## Notes

- `ct` ∈ `{k562, hepg2, hspc}` in v1. To score a new cell type, supply its chromatin tracks (the
  durability model is cell-type-agnostic in *function*, cell-type-specific in *inputs*).
- Validated safe harbours (AAVS1 = `PPP1R12C`, CCR5) score highly writable; clinical genotoxic loci
  (LMO2, MECOM) score near zero — recovered blind, never trained on those labels.
- `writability` is decomposable: inspect `safety` and `p_durable` separately, never just the composite.
