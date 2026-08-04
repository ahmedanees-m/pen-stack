# Demo atlas (1 chromosome)

`atlas_k562.parquet` here is a **single-chromosome (chr19) slice** of the K562 Writable-Genome atlas,
committed so a fresh clone can run the safe-harbour quickstart without first downloading the full release.
chr19 carries the canonical **AAVS1** safe harbour (the `PPP1R12C` locus, chr19q13.42), so the flagship
"where can I write?" example works out of the box.

- Rows: 58,617 genomic bins (1 kb bins across chr19).
- Columns: `chrom, bin, safety, pred_expression, p_durable, reachable_tier1, writability` - identical
  schema to the full per-cell-type atlas, so every cross-link query runs unchanged.
- Size: ~2 MB.

## Scope (read this)

This demo covers **chr19 only**. Queries for genes on other chromosomes (e.g. CCR5 on chr3, TRAC on
chr14) return empty on purpose - it is a demo, not the genome-wide atlas. For genome-wide queries fetch the
full open release:

```bash
bash scripts/fetch_artifacts.sh                                # installs atlas_<ct>.parquet into data/out/
```

## Use it

The atlas directory is resolved from `PEN_ATLAS_DIR` first, so point it at this folder:

```bash
# from the repo root
PEN_ATLAS_DIR=data/demo python -c "from pen_stack.atlas import crosslink as cl; \
  print(cl.loci_for_gene('AAVS1', 'k562').head())"
```

You should see the writable bins of the AAVS1 / PPP1R12C safe harbour, ranked by writability (top bin
~0.99). The full `data/out/` atlas (when present) always wins over this demo - it is only a fallback for a
fresh clone.

## Provenance

Byte-identical `chrom=='chr19'` slice of `atlas_k562.parquet` from the release-of-record atlas build
(K562 writability model; see `benchmarks/` and the manuscript Methods). Regenerate with:

```python
import pandas as pd
df = pd.read_parquet("data/out/atlas_k562.parquet")
df[df["chrom"] == "chr19"].to_parquet("data/demo/atlas_k562.parquet", index=False)
```
