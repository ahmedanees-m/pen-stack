# Data card: Positioning against prior art (WS-PRIORART)

## Summary
Head-to-head positioning of PEN-STACK against the exact prior tools a reviewer flags — measured, with confidence
intervals, reporting nulls verbatim, and **never** claiming to beat a prior tool on its own endpoint. The
defensible contributions under test are (i) the learned **durability** axis and (ii) the **three-way
integration** (safety × durability × reachability). Stance: *complementarity and concordance*, not superiority.

**Prereg:** [`prereg/ws_priorart.yaml`](../../prereg/ws_priorart.yaml)
(SHA `fa55cb709fb90c60d0a55ee4530529cf452ba7a6d56e54a220e52e92890929fb`, locked before any comparison ran).

## Per-analysis status
| Analysis | Prior tool | What it tests | Status | Result |
|---|---|---|---|---|
| **PA-WS1-A** distinctness | ePRIDICT (efficiency) | is the durability axis distinct from efficiency, or re-deriving it? | ✅ **done** | **DISTINCT** — ρ=0.21, R²=0.04 (96% unexplained), n=7,295 |
| PA-WS1-B added value | ePRIDICT | does durability predict silencing-over-time beyond efficiency? | 🔵 data-gated | needs an independent silencing set (not TRIP) |
| PA-WS2 concordance | GEG-SH | does the integrated score agree with an established safe-harbor score? | ⏳ pending | — |
| PA-WS3 GSH-recovery | validated GSH set | does the integrated score recover experimentally-validated safe harbors? | ⏳ pending | — |
| IntQuery positioning | IntQuery | cryptic-attB nomination | ⛔ not runnable (paper-only) | qualitative only |

## PA-WS1-A — durability vs ePRIDICT (independently substantiated)
ePRIDICT (Mathis et al., *Nat Biotechnol* 2025, `10.1038/s41587-024-02268-2`) predicts prime-editing
**efficiency** from K562 chromatin; PEN-STACK's atlas predicts **durability** (`p_durable = 1 - P(silenced)`).
Both map a genomic location → a chromatin-derived score, so they are comparable *as scores* even though the
endpoints differ. On **7,295 shared K562 loci** (ePRIDICT-light, 6 ENCODE tracks, vs the atlas value read
directly from `phase_1/out/atlas_k562.parquet`):

- Spearman **ρ = 0.212** [0.188, 0.235]; Pearson r = 0.202 [0.179, 0.224]
- Variance partition **R² = 0.041** [0.032, 0.050] → ePRIDICT explains ~4% of durability variance; **96% unexplained**
- Pre-registered decision: **DISTINCT** (`|ρ|<0.30 and R²<0.10`).

Conservative by construction: both models read K562 chromatin and share three marks (H3K4me1, H3K9me3,
H3K27me3), yet the axes still diverge. Honest caveat — at n=7,295 the weak correlation is statistically
significant (p≈1e-75); the claim is *negligible shared variance / distinctness*, not statistical independence.

**Consequence (pre-registered):** keep the durability axis as a distinct/complementary contribution (softened
wording); proceed to GSH-recovery (PA-WS3) + GEG-SH concordance (PA-WS2).

Deposit: [`benchmarks/priorart/epridict/`](../../benchmarks/priorart/epridict/) (metrics JSON, scatter,
7,295 paired scores, raw ePRIDICT output, SHA256SUMS).

## Honest limits (state in the paper)
- **Endpoint mismatch** — efficiency vs durability: distinctness, not superiority.
- **Single-timepoint durability** — `p_durable` is a lower-quartile expression-robustness split, not a measured
  silencing-over-time trajectory (settled gate).
- **Shared lineage / domain shift** — both derive from ENCODE K562 chromatin (3 shared marks); the durability
  model is TRIP-trained on mouse mESC and applied to human K562 marks.
