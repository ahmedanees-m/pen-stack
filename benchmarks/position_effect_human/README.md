# TPE-Bench-Human: the human K562 position-effect head

This is the **human** companion to [`../position_effect/`](../position_effect/) (TPE-Bench, mouse mESC). It records the
held-out benchmark for the **human K562 position-effect expression head** - the twin
`PositionEffectModel` served behind the serving layer when a design targets human K562. This folder lands it as a real, SHA-locked benchmark.

Every number in `metrics.json` is copied verbatim from a source file and each field is annotated with its origin in
`metrics.json -> field_sources`. The source files are listed under `metrics.json -> source_files`.

## The split (sealed, run once)

- **Held out by whole chromosome: `{chr3, chr8, chr12}`**, `n_test = 1506` (leakage control - nearby integrations
  share chromatin), frozen in `split.json` and checksummed in `SHA256SUMS`.
- **Pre-registered + sealed before scoring.** `split.json` carries the prereg seal
  `9a928f8c3129d07fdd427292663921fefb9dd59304838b2525a715329e4c05f5` (from `p2_head_prereg.sealed.json`). The split
  was untouched - never used as a test set - and the model was run on it **once**.
- **Distinct from the mouse-axis null split.** The pre-registered *mouse-axis* `validated_null` (below) used a
  different held-out split `{chr2, chr9, chr16}` (prereg `2a4c722a...`). Do not conflate the two.

## Headline result (fresh sealed held-out)

| Predictor (fresh sealed, run once) | Held-out ρ |
|---|---|
| **Shipped twin model (5 marks) - HEADLINE** | **0.5711** |
| Independent variant (3 active marks; heterochromatin dropped) | **0.558** |
| Baseline - learned multi-feature heterochromatin | 0.493 |
| Baseline - single-feature `lad` | 0.4489 |

**Independent − best baseline = +0.065, bootstrap 95% CI [0.0257, 0.1033] - excludes 0 → `grounded_human_headroom`.**
The circularity-clean model beats a *learned heterochromatin model* on a fresh sealed split. Acceptance criteria:
`tau = 0.2`, `delta = 0.05`. Cross-validated on the shipped head: chromosome-blocked 5-fold **OOF ρ ≈ 0.59**,
split-conformal held-out coverage **0.90** (target 0.90).

## The circularity-guarded learned baseline

The bar is not the trivial single-feature `lad` rule. The **best baseline is a *learned* multi-feature
heterochromatin model** - a LightGBM on `lad + LMNB1-DamID + H3K9me3 + H3K27me3` (ρ 0.493) - i.e. a model that is
itself allowed to learn the "avoid heterochromatin" rule from four repressive/lamina features. The **independent
variant** of the head has those heterochromatin/lamina marks *dropped* (3 active marks only, ρ 0.558), so the +0.065
margin is signal the head extracts **beyond** what a heterochromatin model can, not a re-labelling of the same
repressive axis. This guards against the circularity of "predict silencing from the marks that define silencing."

The **silencing classifier is a null result** (AUROC 0.50, chance): the Leemans escaper/repressed label is not
predictable from chromatin marks, so only the **expression head** ships; the silenced classifier is flagged
not-validated. Top expression features are `H3K36me3, H2AFZ, H3K79me2` (active elongation - biologically sensible).

## The resolution finding (the binding real-world constraint)

The 0.57 head is measured with Leemans **high-resolution per-integration** chromatin features (ChIP at the exact
integration site). A matched-source test (`P2_MATCHED_TRANSFER.json` - ENCODE fold-change features on **both** sides,
same 5 marks, z-scored within dataset) isolates two effects:

| matched-source (ENCODE both sides, 5 marks) | ρ |
|---|---|
| human K562 → human K562 (in-domain) | 0.1595 |
| mouse mESC → mouse mESC (in-domain) | 0.4287 |
| mouse mESC → human K562 (cross-species) | 0.0801 |
| human K562 → mouse mESC (cross-species) | 0.1956 |

1. **Feature *resolution*, not species, is the dominant variable.** On the **coarse 1 kb-binned atlas features the
   serving pipeline uses**, even an *equally human-trained* model on human K562 tops out at **ρ ≈ 0.16**. Realizing
   the 0.57 requires **exact-site feature extraction at serve time** (a future target). The current head makes the serve-time
   scope flag **resolution-aware**: `human_K562_outcome_validated` fires only when the caller declares exact-site
   features; coarse/undeclared features get a downgraded flag.
2. **Cross-species transfer is genuinely poor** (matched-source ~0.08–0.20) - the axis is cell-type/species-specific;
   train a head **per target cell type**. (An earlier confounded read of ρ 0.505 - human van-Steensel vs mouse ENCODE
   features - was a source artifact, corrected here.)

## The pre-registered mouse-axis null (context)

The **shipped mouse-TRIP-trained axis applied cross-species to human K562** is a pre-registered clean negative:
ρ **0.137** vs best baseline `lad` **0.391** (margin −0.254, CI [−0.321, −0.181]) → **`validated_null`** (prereg
`2a4c722a...`, held-out `{chr2, chr9, chr16}`). This is exactly what the two constraints above predict (coarse
features × cross-species = the floor), and it is *why* a human-trained head was built. It is **not** "we
validated `p_durable`."

## Result (the sentence to use)

> The shipped **mouse-trained** durability axis **fails to transfer to human K562** (pre-registered `validated_null`,
> ρ 0.14). A **human-trained head** - cross-validated on held-out human chromosomes, circularity-clean, on a fresh
> sealed split - predicts K562 position-effect expression **beyond a learned heterochromatin model** (shipped ρ ≈ 0.57;
> +0.065 over the heterochromatin baseline, CI clean). This is genuine human-cell headroom - **K562/Leemans only**,
> and realizing it in production requires exact-site chromatin features (coarse 1 kb bins drop even a human model to
> ρ ≈ 0.16).

## Data provenance - Leemans 2019

- **Leemans et al., 2019, *Cell*** - "Promoter-Intrinsic and Local Chromatin Features Determine Gene Repression in
  LADs." DOI `10.1016/j.cell.2019.03.009`; PMID `30982597` (verified in
  `DATA_ID_VERIFICATION_2026-07-04.md`). Human K562 TRIP, ~9,298 integration loci; per-integration expression +
  chromatin features from the van Steensel lab GitHub, **integration coordinates from Cell supplement Dataset S2**
  (`mmc4.zip` / OSF `6qwj2`), lifted **hg19 → hg38** (9,230 kept).
- Labels are the **measured** TRIP steady-state expression - never a model claim (non-circular).
- **Single dataset / single cell type.** The fresh-split + learned-heterochromatin-baseline design removes the
  within-dataset p-hacking concern; a second same-processing human cell type is genuinely unavailable in the
  accessible literature (searched, not found - stated as a limitation, not claimed as done).

## Scope & limits

- Steady-state position-effect expression in **K562 only**; not temporal durability, not other cell types.
- The **served** ρ 0.57 requires exact-site per-locus features; coarse 1 kb atlas bins realize only ρ ≈ 0.16 (the
  serve-time flag is resolution-gated so the claim cannot exceed the served resolution).
- The transfer probe is **cross-species** (human K562 ↔ mouse mESC); a same-processing second human cell type would be
  the ideal clean generalization probe.

## Files

| file | description |
|---|---|
| `metrics.json` | all held-out numbers, each field annotated with its source file+path (`field_sources`) |
| `split.json` | the sealed `{chr3, chr8, chr12}` held-out split (n=1506) + prereg seal + acceptance rule |
| `SHA256SUMS` | integrity hashes. Two of its entries no longer match current bytes: this manifest was not regenerated as the benchmark evolved, so `sha256sum -c` reports those two as failures. Both are accounted for by name in the deposit's benchmark-manifest provenance record. The manifest enforced by `make repro` is `benchmarks/genome_writing_bench/SHA256SUMS`, which verifies clean. |
| `README.md` | this file |

Shipped model `pen_stack.twin.position_effect`. Data license: see [`../../DATA_LICENSES.md`](../../DATA_LICENSES.md).
