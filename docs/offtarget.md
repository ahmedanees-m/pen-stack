# The off-target nomination engine (v6.10 PEN-OFFTGT)

The off-target nomination engine completes the **safety triad** (site, writer, and off-target) by turning
off-target from a single-family bridge pseudosite scan into a **cross-writer-family, chromatin-aware NOMINATION
engine** with a real-data-calibrated risk band. The cardinal invariant: **nomination is not a clearance.**
A nominated off-target is a candidate, and every result ships with the empirical assay that would confirm it.

## The engine (`pen_stack/wgenome/offtarget_predict.py`)

`nominate_offtargets(writer_family, ...)` dispatches by writer family:

- **Nuclease (Cas9):** given a guide + candidate sites (e.g. from a Cas-OFFinder scan), each candidate gets a
  **mismatch-calibrated empirical risk** (the real active fraction at *k* mismatches, not a guessed curve), the
  **real CRISOT-Score** when the (guide, site) is in the cached bench, and a documented **chromatin-accessibility
  modifier** (open chromatin raises realized off-target activity; Lazzarotto 2020). The modifier reads the **real
  accessibility track** (`phase_1/features/chromatin_{ct}.parquet`) when a candidate's genomic locus + cell
  type are supplied and the store is present, accepts a caller-supplied scalar otherwise, and **abstains** when
  neither is available (the bare wheel / current deployed atlas do not ship the raw track). A controlled validation
  (off-targets mapped to hg38; AUROC of accessibility for active-vs-inactive off-targets, in-vitro negative
  controls) found that with a **cell-type-matched** track (ENCODE HEK293T DNase, v6.10.3) accessibility predicts
  WT-Cas9 cell-based off-target activity: **GUIDE-seq AUROC 0.58 (cross-cell K562) → 0.671 (matched), CI
  [0.642, 0.701]**, in-vitro control null. **VALIDATED (moderate, cell-type-matched)**; it is surfaced as an
  annotation and does **not yet change the numeric risk score** (sequence/CRISOT dominates; TTISS, a Cas9-variant
  assay, is the expected outlier). Full result: `benchmarks/offtarget/chromatin_validation.json`.
- **Serine integrase (Bxb1):** a cryptic **pseudo-attB** scan that seeds on the *real documented* Bxb1 attB core
  (`GCGGTCTC`, central GT; FlyBase FBto0000359, Ghosh 2003) and reports candidate cryptic sites by arm mismatches.
- **Bridge recombinase:** delegates to the existing Perry-DMS pseudosite engine (`pen_stack.bridge.offtarget`).

The engine **abstains without inputs** (no candidate sites → no fabricated sites) and is explicit that genome-wide
candidate ENUMERATION needs the on-VM scan; this engine SCORES + RANKS + risk-bands supplied candidates.

## The benchmark (real data + real tool)

`benchmarks/offtarget/` is a held-out-guide nomination benchmark over **four** unbiased assays: GUIDE-seq +
CIRCLE-seq (canonical guides) and CHANGE-seq + SITE-seq (**independent broad guide panels**, a cross-assay test).
The licensed **CRISOT-Score** predictor (CC-BY-NC, run on the VM; MD-physics and **assay-agnostic** → leakage-clean)
beats the sequence-homology baseline on **all four**: AUPRC 0.65/0.52/0.54/0.52 vs 0.47/0.27/0.25/0.23, with the
per-guide bootstrap CI on the gap excluding 0 on each. The Off-Target-Bench also contributes a nomination task to the
**Genome-Writing Challenge**. Only derived CRISOT scores are cached/committed; the weights are never redistributed.
A genomic-coordinate locus split is not possible (the harmonized data ships sequences, not coordinates); held-out-
guide + cross-assay is the leakage-clean evaluation. See `docs/cards/offtarget_data.md` for full provenance.

## Validation-assay recommendation (`pen_stack/wgenome/offtarget_assay.py`)

`recommend_assay(writer_family)` maps a writer to the empirical assay(s) that would confirm a nomination
(GUIDE/CHANGE/CIRCLE-seq for nucleases, Cryptic-seq/HIDE-seq for serine integrases) and is **explicit about the gap**
for bridge recombinases: there is no published genome-wide unbiased off-target assay or predictor for them, so their
nominations are flagged extrapolative and routed to targeted confirmation, never read as a clearance.

## Surfaces
REST `POST /offtarget` + `GET /offtarget/assay`, MCP `offtarget_scan`, manifest tool `nominate_offtargets`
(`fabricates: false`), the `offtarget_nomination` scope card, and the **Off-Target** web page.

## Limitations
Nomination ≠ validation. Bridge/integrase off-target is data-thin/unmodeled (verified) and flagged extrapolative.
Chromatin-awareness depends on target-cell-type data. Translocations/structural variants beyond nominated sites are
out of scope. The CRISOT learned predictor is CC-BY-NC and runs only on the VM; PEN-STACK ships only derived scores.
