# AlphaGenome feasibility + integration-mode decision

*Prepared 2026-06-04. Decision: **hybrid** (API on-demand per locus; measured-ENCODE atlas stays the backbone).*

## What was tested

| Check | Result |
|---|---|
| API key + client | `dna_client.create(key)` opens a **gRPC channel to the hosted AlphaGenome server**; authenticated and serving. |
| Local model / weights | **None.** `jax` is not installed locally and no weights are downloaded - inference runs on Google's infrastructure, returned over gRPC. |
| Output types | Confirmed: `ATAC, CAGE, DNASE, RNA_SEQ, CHIP_HISTONE, CHIP_TF, SPLICE_SITES, SPLICE_SITE_USAGE, SPLICE_JUNCTIONS, CONTACT_MAPS, PROCAP`. |
| Tracks the atlas needs | All present for K562 (`EFO:0002067`) and HepG2 (`EFO:0001187`): `ATAC`, `DNASE`, and the five histone marks via `CHIP_HISTONE` (`histone_mark` in {H3K27ac, H3K4me1, H3K4me3, H3K9me3, H3K27me3}). |
| Contact maps | `CONTACT_MAPS` returned for 1 Mb intervals (3D structural-risk signal for C3). |
| Mouse support | `MUS_MUSCULUS` works; **ES-Bruce4 RNA-seq (`EFO:0005483`)** is an exact match to the TRIP supervision cell line, used by the endogenous-expression baseline. |
| Supported context lengths | 16 KB / 100 KB / 500 KB / 1 MB. |
| Latency | ~1-3 s per interval prediction over the network; comfortably within the free-tier rate limit for per-locus use. |

## The 16 GB-GPU question (local 1 Mb JAX inference)

A local 1 Mb forward pass on a 16 GB card would be very tight on memory - but **we do not run AlphaGenome
locally**. Our usage is the hosted API only (thin client + a small on-disk cache). The 16 GB local GPU is
never asked to hold a 1 Mb activation tensor. The concern only applies to the *stretch* option below.

## Decision: hybrid (the plan's default)

- **Backbone unchanged.** The genome-wide writability atlas stays on **measured ENCODE tracks** (already
  built, three cell types). AlphaGenome does not replace it.
- **AlphaGenome invoked on-demand per locus** for: (a) the endogenous-expression durability baseline (already
  done); (b) predicted-vs-measured track validation; (c) 3D contact-map deltas at candidate sites;
  (d) track prediction in cell types lacking measured data.
- **Caching for reproducibility.** Every call is keyed by `(assembly, interval, output, ontology,
  center_bp, model_version)` and the reduced features are written to `data/alphagenome_cache/`. A cache hit
  reproduces identical outputs offline and respects quota; the provider exposes an `offline=True` mode so
  CI and `run()` never touch the network.

### Stretch (not taken now)
A one-time genome-wide precompute for one extra cell type would need local GPU inference; on a 16 GB card a
1 Mb context is impractical. If pursued later, the realistic routes are the A100/VM tier or a shorter
(100-500 KB) context. It is not required: the measured-track atlas is the backbone.

### Fallback
If the API became unavailable, Enformer/Borzoi-pytorch are the substitute, stated explicitly. AlphaGenome
availability **does not block the cycle**.

## Implications honored downstream
- Cross-cell-type writability claims are **bounded by AlphaGenome's training coverage** (recorded as a scope note).
- 3D structural risk ships as a **flag with confidence, never a hard pass/fail**; it is a
  heuristic, not a calibrated probability, and is not validated against insertion-induced hijacking
  (no ground-truth dataset exists), only sanity-checked on known hijacking loci.
