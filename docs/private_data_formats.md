# Private data formats for local adaptation (WS-F1)

PEN-STACK can recalibrate (or lightly fine-tune) its released safety/durability scores on **your own
assays**, entirely in-container, so the data never leaves your machine. This page documents the input
formats. The adaptation itself (`pen_stack.adapt`) only ever writes to `models/local_<id>/` and never
touches the released model.

## The tabular schema (what the code consumes)

`pen_stack.adapt.ingest.load_user_labels(path)` reads `.csv` / `.tsv` / `.parquet` with these columns:

| column | required | meaning |
|---|---|---|
| `chrom` | yes | chromosome (e.g. `chr2`) |
| `bin` **or** `pos` | yes | 1 kb bin index, or a base position (converted to a bin at 1 kb) |
| `label` | yes | outcome: `0/1` (e.g. silenced/expressed, off-target/clean) or a probability in `[0,1]` |
| `ct` | no | cell type (default `user`) |
| `score` | no | the released model's output for that site; if absent it is joined from the atlas |
| *feature cols* | no | only needed for the optional `finetune` method |

Example (`my_sites.csv`):

```csv
chrom,pos,label
chr2,121000123,1
chr11,5200900,0
chr19,55115768,1
```

## Deriving labels from raw assays (runs in the Docker image)

The upstream conversion to the tabular schema above uses standard tools already in the image. These are
**documented pipelines**, not new methods:

- **Integration-site sequencing** (durability/expression-stability): align reads (`bwa`/`minimap2`),
  call integration sites, quantify per-site expression/silencing over time, threshold to a `label`
  (`1` = stably expressed, `0` = silenced). Emit `chrom,pos,label`.
- **GUIDE-seq / off-target capture** (safety): align, call cleavage/insertion sites, label measured
  off-targets `1` and matched non-sites `0`. Emit `chrom,pos,label`.
- **Expression-stability profiles** (FASTQ/BAM): per-site expression summary → continuous `label` in
  `[0,1]` (a calibration target).

Each pipeline's only contract is: **produce the tabular schema**. Once you have that table, the in-code path
(`adapt.ingest` → `adapt.adapt`) handles feature attachment, the held-out split, recalibration/fine-tuning,
the validation gate, and versioned output.

## Run the adaptation

```python
from pen_stack.adapt import adapt
from pen_stack.adapt.ingest import load_user_labels, attach_features

df = attach_features(load_user_labels("my_sites.csv"), target="safety", ct="k562")
report = adapt(df, target="safety", method="isotonic", local_id="lab1")   # or method="finetune"
# report["gate"]["decision"] tells you whether the adapted model was ACTIVATED or REJECTED;
# artifacts + model card are under models/local_lab1/. The released model is provably unchanged.
```

The adapted model **activates only if it beats the released model AND a no-skill constant predictor** on
your held-out split (chromosome-grouped when possible) — otherwise it is rejected and the released model is
kept. `models/local_<id>/` is git-ignored: your private adaptations stay local.
