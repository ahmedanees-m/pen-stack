# Data card: Writer-Efficiency dataset

The curated, literature-sourced integration-efficiency table behind the writer-efficiency model (`pen_stack/atlas/writer_efficiency.py`
→ `data/writer_efficiency.parquet`). One row = one **measured** integration-efficiency condition. **No fabrication:
every row carries a DOI, a verbatim source quote, and a source-access grade.**

## Schema
`system, family, write_type, variant, cargo_bp, locus, cell_type, organism, delivery, efficiency_pct,
efficiency_raw, specificity_pct, source_access, doi, quote`. `efficiency_pct` is % integration in the stated cell
type; ranges (e.g. "~10-20%", "4-22%") are stored as their **midpoint** with the raw string in `efficiency_raw`.
A one-sided bound (e.g. "up to 20%", ">6%") is stored as the stated bound itself, so 15 of the 45 rows
carry a bounded rather than a point label, 11 of them `pmc_verbatim`. Read `efficiency_raw` wherever the
distinction between a point value and a bound matters.

## Source-access grades (provenance quality, per row)
| Grade | Meaning | n |
|---|---|---|
| `pmc_verbatim` | quoted from the open-access PMC full text (highest confidence) | 39 |
| `abstract` | quoted from the published abstract | 1 |
| `secondary` | reliable secondary source where the primary is paywalled (flagged; droppable via `strict=True`) | 5 |

**Grade and family are not separable.** All six records that are not `pmc_verbatim` belong to `bridge_IS110`, and
that family carries no `pmc_verbatim` record, so a subset taken on source grade is also a subset taken on family.
`strict=True` is therefore a high-confidence subset and not a provenance control: it leaves `bridge_IS110` a
single record and the cross-family fold degenerate. The structure and what it does and does not permit are set
out in `benchmarks/writer_efficiency/provenance_sensitivity.json`. Two consequences carry into the evaluation:
the held-out-locus axis contains no non-primary record at all, because every non-primary human record sits at an
aggregate pseudo-locus that the specific-locus mask already excludes, and the held-out-family result spans zero
both on the full table and on the three families carrying full primary-source provenance.

**Figures confirmed against the primary texts.** The four `secondary` human-cell figures match their sources:
6.82% and 14.76% are the enIS621-tebRNA averages over AAVS1 site3 and B2M intron 1 in HEK293T and in Jurkat T
cells, open in PMC13396178; insertion above 6% is the ISCro4 figure in Pelea et al.; and up to 20% insertion with
82% specificity is the engineered ISCro4 figure in Perry et al. The 27.75% figure appears in the enIS621 abstract
and nowhere in that paper's results or methods, which is the grade the row carries.

## Coverage (~45 records, 42 human-cell, 9 DOIs, 4 families)
| Family | n | Representative systems |
|---|---|---|
| PE_integrase | 23 | PASTE, PASSIGE / evoPASSIGE / eePASSIGE |
| serine_integrase | 11 | Bxb1 (WT + evolved combination), PhiC31 (P2/P3 evolved), eeBxb1 V105I |
| bridge_IS110 | 6 | ISCro4, IS621 / enIS621 |
| CAST_VK | 5 | ShCAST (E. coli), PseCAST / evoCAST |

Loci: AAVS1, CCR5, ROSA26, ACTB, LMNB1, ALB, TRAC, GBA1, FANCA, B2M, COL7A1, Xq22.1, … · Cell types: HEK293T/FT,
K562, Jurkat, HepG2, N2a, iPSC, primary T / hepatocyte / fibroblast, E. coli.

## Primary sources (all citation-verified 2026-06-19)
| Source | DOI | Access |
|---|---|---|
| Yarnall et al., *Nat Biotechnol* 2023 (PASTE) | 10.1038/s41587-022-01527-4 | PMC10257351 (verbatim) |
| Pandey/Gao/Krasnow/Liu et al., *Nat Biomed Eng* 2025 ((ee)PASSIGE) | 10.1038/s41551-024-01227-1 | PMC11754103 (verbatim) |
| Hew et al., *Nucleic Acids Res* 2024 e64 (hyperactive integrases) | 10.1093/nar/gkae534 | PMC (verbatim) |
| evoCAST, *Science* 2025 | 10.1126/science.adt5199 | PMC12326709 (verbatim) |
| Strecker et al., *Science* 2019 (ShCAST) | 10.1126/science.aax9181 | PMC6659118 (verbatim) |
| enIS621, *Nat Commun* 2026 | 10.1038/s41467-026-74164-z | abstract (27.75%) + secondary (per-cell-type) |
| ISCro4, *Science* (Pelea adz1884 / Perry adz0276) | 10.1126/science.adz1884, 10.1126/science.adz0276 | secondary (paywalled) |
| Durrant et al., *Nature* 2024 (bridge RNA, IS621 in E. coli) | 10.1038/s41586-024-07552-4 | secondary |

## Limitations
- **Small & literature-sourced.** ~42 human-cell records / 4 families: the binding statistical limit for the
  cross-family transfer claim (reported, not hidden). The dataset + bench are the contribution.
- **Range-midpoint handling** for efficiencies reported as ranges (raw string retained).
- **Heterogeneous assays/conditions** across papers (delivery, cargo, pre-installed vs PE-installed att): encoded
  as features (`variant`, `delivery`, `cargo_bp`) + a covariate, but cross-paper variance is real.
- **secondary-source rows** (bridge ISCro4/IS621) are flagged and excluded under `strict=True`. Because they are
  one family, excluding them removes that family rather than isolating provenance quality, so `strict=True` is a
  confidence subset and not a provenance control.
- **No per-row experimental uncertainty.** No column carries a replicate count, standard deviation or interval,
  so measurement error cannot be propagated into a downstream analysis.
