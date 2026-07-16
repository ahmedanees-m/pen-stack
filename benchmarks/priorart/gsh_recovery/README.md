# GSH-recovery enrichment

**Prereg:** [`prereg/ws_priorart.yaml`](../../../prereg/ws_priorart.yaml) `analysis_WS3`
(SHA-locked `33fb67b8…`; the frozen coordinate sets were hashed *before* the atlas lookup).

## Question
Does the PEN-STACK integrated score (**writability** = 0.5·safety + 0.5·p_durable, from the K562 atlas) rank
experimentally-validated genomic safe harbors **above the random genomic background**, and rank known
insertional-oncogenesis loci **low**?

## Sets (independently verified, see `data/priorart/gsh_sets.csv`)
- **7 validated GSH positives (hg38):** AAVS1 (chr19:55,115,785), Pansio-1 (chr1:113,340,237),
  Olônne-18 (chr18:56,410,860), Keppel-19 (chr19:5,401,450), Autio *eLife* 2024 `10.7554/eLife.79592`;
  SHS231 (chr4:58,110,456), SHS229 (chr2:45,481,224), SHS253 (chr2:48,603,055), Pellenz *Hum Gene Ther*
  2019 `10.1089/hum.2018.169` (hg19→hg38 lifted). AAVS1 canonical `10.1038/nbt.1562`.
  *All DOIs Crossref-verified; all coordinates Ensembl-verified. Rogi1/2 (Aznauryan) omitted, exact bp exist
  only in a figure image / supplementary CSV; not fabricated.*
- **5 known-unsafe hard negatives:** LMO2, MECOM, CCND2, HMGA2, PRDM16 (insertional-oncogenesis gene TSS).
- **2,000 background:** uniform random atlas bins (seed 20260702), excluding ±10 bins of any pos/unsafe.

## Result (reported verbatim)

**Primary, recovery above background (pre-registered): `NULL`.**

| axis | AUROC (pos vs background) | 95% CI | permutation p | decision |
|---|---|---|---|---|
| **writability** | **0.369** | [0.196, 0.598] | **0.887** | **NULL** |
| safety | 0.508 | - | - | (saturated: 98.5% of background is also safety=1.0) |
| p_durable | 0.359 | [0.181, 0.593] | 0.900 | - |
| ePRIDICT efficiency | 0.592 | [0.390, 0.779] | 0.202 | NULL |

The integrated score does **not** enrich validated GSH above the random genome: a random genomic position is
already mostly "safe + moderately durable," so validated GSH do not stand out from the bulk safe genome. ePRIDICT
efficiency also fails to recover GSH.

**Secondary, the known-unsafe control is perfect.** All 5 oncogene loci land at the **0th percentile** of
background writability, and validated GSH separate from known-unsafe loci with **AUROC = 1.0** [1.0, 1.0]
(driven entirely by the safety axis: GSH = 1.0, oncogenes = 0.0). Durability does **not** separate them
(p_durable AUROC 0.31; oncogenes are transcriptionally active, hence *more* durable), consistent with the distinctness finding
(durability is a distinct axis, not a generic "goodness" score).

## Interpretation
The integrated score's safe-harbor value is in **rejecting unsafe loci** (near-oncogene, active), not in ranking
validated GSH above the generically-safe *bulk* intergenic genome, against a uniform-random background the
validated GSH sit mid-distribution (mean 0.856 vs background mean 0.859), so they do not stand out. This is
specific to the uniform-random negative: the negative matters. The platform's own `blind_gsh_discovery`
benchmark (`pen_stack/validate/blind_gsh_discovery.py`, prereg `ws_a.yaml`) scores validated GSH against
**controls matched on distance-to-TSS, distance-to-oncogene, and accessibility** and does recover them above
those matched controls (AUROC ≈ 0.68). So the complete, reconciled picture is: the integrated score **rejects
known-unsafe loci** (AUROC 1.0 here; genotoxic-CIS at the ~1st percentile in the atlas card) and **beats
confounder-matched controls** (~0.68), but does **not** rank validated GSH above the already-safe bulk genome
(0.37 here), because most of the genome is, by these axes, already safe. All three results are reported verbatim.

## Limitations
- Small positive set (n=7) → limited power; leave-one-out + permutation + full CIs; conclusions caveated.
- Validated GSH were characterized in hESC/HEK293T/Jurkat and are scored here on the **K562** atlas as a proxy
  (safety axis is largely cell-type-general; durability is K562-specific).
- Known-unsafe = oncogene TSS, a coarse proxy for insertional-oncogenesis risk.

## Files
| file | description |
|---|---|
| `gsh_recovery_metrics.json` | AUROC/AUPRC + permutation + LOO + bootstrap CIs + positive-vs-unsafe + DeLong-style Δ |
| `gsh_recovery.png` | writability distribution: background vs validated GSH vs known-unsafe |
| `gsh_scored_loci.csv` | every set locus with atlas safety/p_durable/writability + ePRIDICT efficiency |
| `SHA256SUMS` | integrity hashes |
