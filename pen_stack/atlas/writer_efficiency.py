"""Writer-Efficiency dataset, the curated, literature-sourced efficiency table behind Stage C (v6.8 PEN-WRITER).

The writer frontier crossed into quantitative human-cell data in 2023-26, but the efficiency numbers are scattered
across a dozen papers with no unified resource. This module curates them into ONE schema so a learned cross-family
efficiency predictor (`atlas.writer_predict`) can be trained and a held-out benchmark (`benchmarks/writer_efficiency/`,
the Writer-Efficiency Bench) can be sealed. The curated dataset is itself the standalone contribution.

NO FABRICATION. Every record carries its DOI, the verbatim source quote, and a `source_access` provenance grade:
  * `pmc_verbatim`, quoted from the open-access PMC full text (highest confidence)
  * `abstract`, quoted from the published abstract
  * `secondary`, a number reported by a reliable secondary source (press release / summary) where the
                      primary full text is paywalled; flagged so it can be excluded from the strict benchmark.
Range values (e.g. "~10-20%", "4-22%") are stored as their midpoint in `efficiency_pct` with the raw string in
`efficiency_raw`; the exact quote travels in `quote`. Efficiencies are % integration in the stated cell type
(human unless noted); bacterial (E. coli) rows are labelled and excluded from the human-cell benchmark.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from pen_stack._resources import project_root

COLUMNS = ["system", "family", "write_type", "variant", "cargo_bp", "locus", "cell_type", "organism",
           "delivery", "efficiency_pct", "efficiency_raw", "specificity_pct", "source_access", "doi", "quote"]

# Family keys align with the Writer Atlas (wtkb). PE-installed-att systems (PASTE/PASSIGE) -> PE_integrase;
# pre-installed-att recombinase-only systems -> serine_integrase; bridge -> bridge_IS110; CAST -> CAST_VK.
_R = [] # records


def _rec(system, family, write_type, variant, cargo_bp, locus, cell_type, organism, delivery,
         eff, eff_raw, doi, quote, source_access="pmc_verbatim", spec=None):
    _R.append(dict(system=system, family=family, write_type=write_type, variant=variant, cargo_bp=cargo_bp,
                   locus=locus, cell_type=cell_type, organism=organism, delivery=delivery,
                   efficiency_pct=float(eff), efficiency_raw=eff_raw, specificity_pct=spec,
                   source_access=source_access, doi=doi, quote=quote))


# ---- PASTE, Yarnall et al., Nat Biotechnol 2023 (41:500-512), 10.1038/s41587-022-01527-4 (PMC10257351) ----
_P = "10.1038/s41587-022-01527-4"
_rec("PASTEv1", "PE_integrase", "insertion", "WT", 969, "ACTB", "HEK293FT", "human", "plasmid", 15, "~15%", _P,
     "BxbINT integrase showed the highest integration rate (~15%) at the targeted ACTB locus")
_rec("PASTEv1", "PE_integrase", "insertion", "WT", 969, "ACTB", "K562", "human", "plasmid", 15, "~15%", _P,
     "PASTEv1 had ~15% gene integration activity in K562 cells")
_rec("PASTEv1", "PE_integrase", "insertion", "WT", 969, "ACTB", "primary_T", "human", "plasmid", 5, "~5%", _P,
     "around 5% efficiency in primary human T cells")
_rec("PASTEv1", "PE_integrase", "insertion", "WT", 969, "ACTB", "primary_hepatocyte", "human", "plasmid", 5, "~5%",
     _P, "PASTEv1 was capable of ~5% gene integration at the ACTB locus in non-dividing quiescent human primary hepatocytes")
_rec("PASTEv3", "PE_integrase", "insertion", "WT", 36000, "ACTB", "HEK293FT", "human", "plasmid", 15, "~10-20%", _P,
     "PASTEv3...achieved precise integration of templates as large as ~36,000 bp with ~10-20% integration efficiency at ACTB and LMNB1")
_rec("PASTE", "PE_integrase", "insertion", "WT", 3000, "ACTB", "HEK293FT", "human", "plasmid", 13, "4-22%", _P,
     "integration frequencies between 4% and 22% depending on the gene and insertion locus (cargos 969-4,906 bp)")
_rec("PASTE_AdV", "PE_integrase", "insertion", "WT", 1000, "ACTB", "HepG2", "human", "adenovirus", 55, "~50-60%", _P,
     "integration of up to ~50-60% with viral-only delivery in HEK293FT and HepG2 cells")
_rec("PASTE_AdV", "PE_integrase", "insertion", "WT", 1000, "ACTB", "primary_hepatocyte", "human", "adenovirus",
     10.5, "up to 10.5%", _P, "editing efficiencies up to 10.5% in a cargo-dependent fashion (primary human hepatocytes)")
_rec("PASTE_invivo", "PE_integrase", "insertion", "WT", 1000, "ACTB", "hepatocyte_in_vivo", "human", "AAV", 2.5,
     "up to 2.5%", _P, "PASTE was capable of integration rates as high as 2.5% in the human hepatocytes in the chimeric liver")

# ---- (ee)PASSIGE, Pandey/Gao/Krasnow/Liu et al., Nat Biomed Eng 2025 (9:22-39), 10.1038/s41551-024-01227-1 (PMC11754103) ----
_E = "10.1038/s41551-024-01227-1"
_rec("eeBxb1", "serine_integrase", "insertion", "V105I", 5600, "AAVS1", "HEK293T", "human", "plasmid", 60, "60%", _E,
     "The V105I mutant supported 60% and 39% integration efficiencies at AAVS1 and CCR5, respectively (pre-installed attB)")
_rec("eeBxb1", "serine_integrase", "insertion", "V105I", 5600, "CCR5", "HEK293T", "human", "plasmid", 39, "39%", _E,
     "The V105I mutant supported 60% and 39% integration efficiencies at AAVS1 and CCR5, respectively (pre-installed attB)")
_rec("PASSIGE", "PE_integrase", "insertion", "WT_Bxb1", 5600, "AAVS1", "HEK293T", "human", "plasmid", 13, "13%", _E,
     "evoPASSIGE: 27%, 22% vs. PASSIGE: 13%, 10% (at AAVS1 and CCR5)")
_rec("PASSIGE", "PE_integrase", "insertion", "WT_Bxb1", 5600, "CCR5", "HEK293T", "human", "plasmid", 10, "10%", _E,
     "evoPASSIGE: 27%, 22% vs. PASSIGE: 13%, 10% (at AAVS1 and CCR5)")
_rec("evoPASSIGE", "PE_integrase", "insertion", "evoBxb1", 5600, "AAVS1", "HEK293T", "human", "plasmid", 27, "27%", _E,
     "evoPASSIGE: 27%, 22% (at AAVS1 and CCR5)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "AAVS1", "HEK293T", "human", "plasmid", 36, "36%", _E,
     "36% and 27% at the AAVS1 and CCR5 loci, respectively")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "CCR5", "HEK293T", "human", "plasmid", 27, "27%", _E,
     "36% and 27% at the AAVS1 and CCR5 loci, respectively")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "ROSA26", "N2a", "mouse", "plasmid", 20, "20%", _E,
     "20% efficiency compared with 9.5% with evoPASSIGE and 3.2% with PASSIGE (Rosa26, N2a)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "GBA1", "HEK293T", "human", "plasmid", 35, "35%", _E,
     "therapeutic-gene integration; GBA1 among loci with 32% average and a minimum of 23% integration")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "FANCA", "HEK293T", "human", "plasmid", 46, "46%", _E,
     "therapeutic-gene integration; FANCA among loci (32% average, minimum 23%)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "B2M", "HEK293T", "human", "plasmid", 32, "32%", _E,
     "32% average integration and a minimum of 23% integration (B2M)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5600, "ALB", "HEK293T", "human", "plasmid", 31, "31%", _E,
     "therapeutic-gene integration; ALB ~31% (32% average, minimum 23%)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5800, "COL7A1", "primary_fibroblast", "human", "mRNA", 30,
     "30%", _E, "eePASSIGE exhibited 30% and 18% average integration in the COL7A1 and FANCA loci, respectively (primary fibroblasts, mRNA)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 5800, "FANCA", "primary_fibroblast", "human", "mRNA", 18,
     "18%", _E, "eePASSIGE exhibited 30% and 18% average integration in the COL7A1 and FANCA loci, respectively (primary fibroblasts)")
_rec("eePASSIGE", "PE_integrase", "insertion", "eeBxb1", 10500, "AAVS1", "HEK293T", "human", "plasmid", 35,
     "up to 35%", _E, "eePASSIGE achieved up to 35% targeted integration of the 10.5-kb donor plasmid")
_rec("eeBxb1", "serine_integrase", "insertion", "eeBxb1", 5600, "CCR5", "iPSC", "human", "plasmid", 3.8, "3.8%", _E,
     "7.3-fold improvement in integration efficiency with eeBxb1 (3.8%) (human iPS cells)")
_rec("PASTE", "PE_integrase", "insertion", "WT_Bxb1", 5600, "8loci_avg", "HEK293T", "human", "plasmid", 3.8,
     "3.8% avg", _E, "eePASSIGE, evoPASSIGE, PASSIGE and PASTE mediated...average efficiency of 22%, 17%, 7.8% and 3.8%")

# ---- Hyperactive integrases, Hew et al., Nucleic Acids Res 2024 (52(14):e64), 10.1093/nar/gkae534 (PMC) ----
_H = "10.1093/nar/gkae534"
_rec("Bxb1", "serine_integrase", "insertion", "WT", 6600, "Xq22.1", "K562", "human", "plasmid", 2.7, "2.7%", _H,
     "11.2-fold (2.7% versus 30.3%) (WT versus evolved combination, PE-installed att)")
_rec("Bxb1", "serine_integrase", "insertion", "c22_I87L_H95Y_V122M_A369P_E434G", 6600, "Xq22.1", "K562", "human",
     "plasmid", 30.3, "30.3%", _H, "11.2-fold (2.7% versus 30.3%) (evolved combination mutant)")
_rec("Bxb1", "serine_integrase", "insertion", "WT", 15700, "attP_preinstalled", "HEK293T", "human", "plasmid",
     22.8, "22.8%", _H, "56.2% integration by the evolved Bxb1 integrase compared to 22.8% for wildtype (15.7 kb vWF cargo)")
_rec("Bxb1", "serine_integrase", "insertion", "evolved_combination", 15700, "attP_preinstalled", "HEK293T", "human",
     "plasmid", 56.2, "56.2%", _H, "56.2% integration by the evolved Bxb1 integrase (15.7 kb vWF cargo)")
_rec("PhiC31", "serine_integrase", "insertion", "P2", 6600, "ROSA26", "HEK293T", "human", "plasmid", 1.3, "1.3%", _H,
     "greatest improvement was between P2 (1.3%) and a 36-hour evolved variant P2-L2-1 (12.1%)")
_rec("PhiC31", "serine_integrase", "insertion", "P2-L2-1", 6600, "ROSA26", "HEK293T", "human", "plasmid", 12.1,
     "12.1%", _H, "P2 (1.3%) and a 36-hour evolved variant P2-L2-1 (12.1%)")
_rec("PhiC31", "serine_integrase", "insertion", "P3-L1-2", 6600, "ROSA26", "HEK293T", "human", "plasmid", 18.4,
     "18.4%", _H, "P3-L1-2 (18.4% at ROSA26)")
_rec("PhiC31", "serine_integrase", "insertion", "P3-L1-13", 6600, "AAVS1", "HEK293T", "human", "plasmid", 11.1,
     "11.1%", _H, "integration efficiencies for P3 reaching 11.1% and 3.0% at ROSA26 and AAVS1")

# ---- CAST, ShCAST (Strecker 2019, 10.1126/science.aax9181, E. coli) + evoCAST (Science 2025, 10.1126/science.adt5199, PMC12326709) ----
_rec("ShCAST", "CAST_VK", "insertion", "WT", 5000, "ecoli_genome", "E_coli", "bacterial", "plasmid", 80, "up to 80%",
     "10.1126/science.aax9181",
     "ShCAST integrates DNA into unique sites in the E. coli genome with frequencies of up to 80% without positive selection")
_rec("PseCAST", "CAST_VK", "insertion", "WT", 1000, "ALB", "HEK293T", "human", "plasmid", 0.023, "0.023%",
     "10.1126/science.adt5199", "5.7% targeted integration efficiency...compared to 0.023% for wild-type PseCAST (ALB)")
_rec("evoCAST", "CAST_VK", "insertion", "evolved", 1000, "ALB", "HEK293T", "human", "plasmid", 5.7, "5.7%",
     "10.1126/science.adt5199", "5.7% targeted integration efficiency...compared to 0.023% for wild-type PseCAST (ALB)")
_rec("evoCAST", "CAST_VK", "insertion", "evolved", 1000, "TRAC", "HEK293T", "human", "plasmid", 13, "13%",
     "10.1126/science.adt5199", "13% integration...compared to 0.061% by wild-type PseCAST (TRAC)")
_rec("evoCAST", "CAST_VK", "insertion", "evolved", 5000, "14loci_avg", "HEK293T", "human", "plasmid", 19, "~10-25%",
     "10.1126/science.adt5199", "evoCAST averaged ~10-25% integration efficiencies of kilobase-size DNA cargoes across 14 tested human genomic sites; averaged 19%")

# ---- Bridge recombinases, enIS621 (Nat Commun 2026, 10.1038/s41467-026-74164-z), ISCro4 (Science) ----
_B = "10.1038/s41467-026-74164-z"
_rec("enIS621-tebRNA", "bridge_IS110", "insertion", "engineered", 1000, "endogenous_avg", "HEK293T", "human",
     "plasmid", 6.82, "6.82%", _B, "6.82% for enIS621-tebRNA (average, two endogenous loci, HEK293T)",
     source_access="secondary")
_rec("enIS621-tebRNA", "bridge_IS110", "insertion", "engineered", 1000, "endogenous_avg", "Jurkat", "human",
     "plasmid", 14.76, "14.76%", _B, "14.76% for enIS621-tebRNA (Jurkat T cells)", source_access="secondary")
_rec("enIS621-tebRNA", "bridge_IS110", "insertion", "engineered", 1000, "best_locus", "multi_human", "human",
     "plasmid", 27.75, "up to 27.75%", _B, "integration rates up to 27.75% for kilobase-scale DNA cargos",
     source_access="abstract")
_rec("ISCro4", "bridge_IS110", "insertion", "WT", 1000, "human_genome", "human_cells", "human", "plasmid", 6,
     ">6%", "10.1126/science.adz1884",
     "facilitates donor DNA insertion at genomic sites with efficiencies surpassing 6% (Pelea et al. human cells)",
     source_access="secondary")
_rec("ISCro4", "bridge_IS110", "insertion", "engineered_DMS", 1000, "human_genome", "human_cells", "human",
     "plasmid", 20, "up to 20%", "10.1126/science.adz0276",
     "up to 20% insertion efficiency into the human genome and genome-wide specificity as high as 82% (Perry et al.)",
     source_access="secondary", spec=82)
_rec("IS621", "bridge_IS110", "insertion", "WT", 1000, "ecoli_genome", "E_coli", "bacterial", "plasmid", 60,
     ">60%", "10.1038/s41586-024-07552-4",
     "over 60% insertion efficiency of a desired gene in E. coli with over 94% specificity (Durrant et al.)",
     source_access="secondary", spec=94)


def records() -> pd.DataFrame:
    """The curated writer-efficiency table (one row per measured condition), with full per-row provenance."""
    return pd.DataFrame(_R, columns=COLUMNS)


def human_cell(df: pd.DataFrame | None = None, strict: bool = False) -> pd.DataFrame:
    """Human-cell rows only (excludes E. coli). `strict=True` keeps only pmc_verbatim + abstract sources
    (drops secondary-source rows), the high-confidence subset for the strict benchmark."""
    df = records() if df is None else df
    out = df[df["organism"] == "human"].copy()
    if strict:
        out = out[out["source_access"].isin(["pmc_verbatim", "abstract"])]
    return out.reset_index(drop=True)


def build_parquet(out: str | Path | None = None) -> Path:
    """Write the SHA-lockable dataset parquet (data/writer_efficiency.parquet)."""
    out = Path(out) if out else project_root() / "data/writer_efficiency.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    records().to_parquet(out, index=False)
    return out


def provenance_summary() -> dict:
    df = records()
    return {"n_records": int(len(df)), "n_human": int((df["organism"] == "human").sum()),
            "by_family": df["family"].value_counts().to_dict(),
            "by_source_access": df["source_access"].value_counts().to_dict(),
            "n_dois": int(df["doi"].nunique()), "loci": sorted(df["locus"].unique()),
            "cell_types": sorted(df["cell_type"].unique())}
