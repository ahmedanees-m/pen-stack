"""Cross-writer-family, chromatin-aware off-target NOMINATION engine (v6.10 PEN-OFFTGT, E-WS2).

One interface over nucleases, serine integrases, and bridge recombinases. By construction:

  * **nuclease** (Cas9): rank candidate off-target sites by the GROUNDED empirical risk (the real-data fraction
    of candidates at k mismatches that were validated-active, `offtarget_data.MISMATCH_ACTIVE_FRACTION`), surface
    the REAL CRISOT-Score when the (guide, site) is in the cached bench, and annotate with a documented
    **chromatin-accessibility signal** (a validated annotation, NOT a re-ranker: open chromatin raises realized
    off-target activity, Lazzarotto 2020, but it added no held-out ranking gain over CRISOT in the v6.10.4
    incremental analysis, so it is not folded into the risk score). The annotation
    reads the **Stage B accessibility track** (`phase_1/features/chromatin_{ct}.parquet`) when a candidate's
    genomic locus + cell type are supplied AND the feature store is present, or accepts a caller-supplied
    accessibility value; it **abstains** otherwise (the bare wheel / current deployed atlas do not ship the raw
    accessibility track). The Off-Target-Bench shows the real CRISOT predictor BEATS the homology baseline on
    FOUR unbiased assays (GUIDE/CIRCLE/CHANGE/SITE-seq; per-guide bootstrap CI excludes 0 on each).
  * **serine integrase** (Bxb1): nominate cryptic **pseudo-attB** sites using the REAL documented Bxb1 attB core
    (GCGGTCTC / central GT), candidate-flagged; the validating assay is Cryptic-seq/HIDE-seq.
  * **bridge / seek**: delegate to the existing Perry-DMS pseudosite engine (`pen_stack.bridge.offtarget`).

A nominated off-target is a CANDIDATE, never a claim, and nomination is **not** a safety clearance, every result
ships with the empirical assay that would confirm it (`offtarget_assay`). Abstains without inputs; never invents
sites. The CRISOT predictor (CC-BY-NC) runs only on the VM; only derived scores are cached.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack.wgenome.offtarget_data import (
    BENCH_SUMMARY,
    bench_records,
    calibrated_active_fraction,
)

_NUCLEASE = {"cas9", "spcas9", "nuclease", "sacas9", "ascas12a", "cas12a", "nickase"}
_INTEGRASE = {"serine_integrase", "bxb1", "phic31", "pe_integrase"}
_BRIDGE = {"bridge_is110", "seek_is1111", "bridge", "is110", "is621", "iscro4"}
_PASTE = {"paste", "passige", "ee_passige", "eepassige", "prime_editing_integrase"}
_CAST = {"cast", "shcast", "vchcast", "evocast", "cast_vk", "cast_v-k", "cast_if", "cas12k", "type_v-k", "type_i-f"}


def _ham20(a: str, b: str) -> int:
    """Mismatches over the 20-nt protospacer (Hamming; ignores the PAM)."""
    a, b = a[:20].upper(), b[:20].upper()
    return sum(1 for x, y in zip(a, b) if x != y)


def _risk_band(active_fraction: float | None) -> str:
    if active_fraction is None:
        return "uncalibrated"
    if active_fraction >= 0.5:
        return "high"
    if active_fraction >= 0.1:
        return "medium"
    if active_fraction >= 0.01:
        return "low"
    return "minimal"


@lru_cache(maxsize=1)
def _crisot_cache() -> dict:
    """(On20, Off20) -> cached real CRISOT score, from the committed bench fixture (VM-computed)."""
    out: dict = {}
    for r in bench_records():
        out[(r["On"][:20].upper(), r["Off"][:20].upper())] = r["crisot_score"]
    return out


@lru_cache(maxsize=8)
def _chromatin_store(ct: str):
    """The Stage B per-cell-type chromatin feature store (chrom,bin -> unified accessibility) + its median, or
    None when the raw track is not present (bare wheel / CI / current deployed atlas). Real, data-gated."""
    try:
        import pandas as pd

        from pen_stack._resources import project_root
        from pen_stack.wgenome.features import add_accessibility
        p = project_root() / "phase_1" / "features" / f"chromatin_{ct.lower()}.parquet"
        if not p.exists():
            return None
        df = add_accessibility(pd.read_parquet(p))
        if "accessibility" not in df.columns:
            return None
        med = float(df["accessibility"].median())
        return df.set_index(["chrom", "bin"]), med
    except Exception: # noqa: BLE001
        return None


def locus_accessibility(chrom: str, bin_idx: int, ct: str = "k562") -> dict | None:
    """REAL Stage B accessibility for a genomic bin (ATAC/DNase), or None (abstain) when the chromatin feature
    store is absent or the bin is off-grid. `accessible` = above the cell-type median (relative, grounded)."""
    store = _chromatin_store(ct)
    if store is None:
        return None
    df, med = store
    try:
        val = float(df.loc[(chrom, int(bin_idx)), "accessibility"])
    except Exception: # noqa: BLE001
        return None
    return {"accessibility_signal": round(val, 4), "cell_type": ct, "median": round(med, 4),
            "accessible": bool(val >= med), "source": "Stage B chromatin_{ct}.parquet (ATAC/DNase)"}


def _chromatin_modifier(accessibility: float | None = None, locus_acc: dict | None = None) -> dict | None:
    """Documented chromatin-accessibility ANNOTATION (NOT a validated quantitative axis): open chromatin raises
    realized off-target activity (Lazzarotto et al. 2020, CHANGE-seq, 10.1038/s41587-020-0555-7). Uses the REAL
    Stage B accessibility (`locus_acc`) when available, else a caller-supplied 0..1 scalar; abstains (None) when
    neither is given. It is QUALITATIVE and does NOT change the numeric risk score, a controlled test on our data
    found the signal weak/inconsistent (see `offtarget_data.CHROMATIN_VALIDATION`)."""
    val = {"validated": True, "effect_size": "moderate", "changes_risk_score": False,
           "validation": "validated standalone (moderate, cell-type-matched: GUIDE-seq off-target AUROC 0.58 "
           "cross-cell -> 0.671 matched HEK293T DNase). ANNOTATION ONLY, v6.10.4 tested the incremental value over "
           "CRISOT: small real conditional signal but NO held-out ranking improvement, so it does NOT change the "
           "numeric risk score (CRISOT sequence score captures the ranking).",
           "doi": "10.1038/s41587-020-0555-7"}
    if locus_acc is not None:
        raises = bool(locus_acc.get("accessible"))
        return {**val, "raises_realized_risk": raises, "source": "stage_b_track",
                "accessibility_signal": locus_acc.get("accessibility_signal"), "cell_type": locus_acc.get("cell_type"),
                "effect": ("accessible (open) chromatin in this cell type -> realized off-target activity tends "
                           "HIGHER for the same sequence match (qualitative; Lazzarotto 2020)" if raises
                           else "inaccessible (closed) chromatin -> realized off-target activity tends lower")}
    if accessibility is None:
        return None
    acc = max(0.0, min(1.0, float(accessibility)))
    raises = acc >= 0.5
    return {**val, "accessibility": round(acc, 3), "raises_realized_risk": raises, "source": "caller_supplied",
            "effect": ("open/accessible chromatin -> realized off-target activity tends HIGHER (qualitative; "
                       "Lazzarotto 2020)" if raises else "closed/inaccessible chromatin -> realized risk tends lower")}


def nominate_nuclease(guide: str, candidate_sites: list[str] | None, accessibility: list[float] | None = None,
                      assay: str = "guideseq", loci: list | None = None, cell_type: str = "k562",
                      top: int = 20) -> dict:
    """Nominate + rank candidate nuclease off-target sites for a guide. ``candidate_sites`` are 20-23-nt genomic
    protospacers (e.g. from a Cas-OFFinder scan). ``loci`` (optional) is a per-candidate (chrom, bin) for the REAL
    Stage B chromatin-accessibility modifier; ``accessibility`` (optional) is a per-candidate 0..1 fallback scalar.
    Abstains (no fabrication) when no candidates are supplied, genome-wide candidate ENUMERATION needs the on-VM
    scan; this engine SCORES + RANKS + risk-bands them."""
    g = (guide or "").upper()
    if len(g) < 20:
        return {"family": "nuclease", "available": False, "abstain": True,
                "note": "guide must be >=20 nt (protospacer)"}
    if not candidate_sites:
        return {"family": "nuclease", "available": False, "abstain": True,
                "note": "no candidate sites supplied, provide Cas-OFFinder/on-VM genome-scan candidates "
                        "(20-23 nt protospacers); this engine scores+ranks+risk-bands them, it does not "
                        "fabricate sites", "method": "homology + real-data mismatch calibration + cached CRISOT"}
    cache = _crisot_cache()
    g20 = g[:20]
    noms = []
    for i, site in enumerate(candidate_sites):
        s = (site or "").upper()
        nmm = _ham20(g20, s)
        af = calibrated_active_fraction(nmm, assay)
        crisot = cache.get((g20, s[:20]))
        locus_acc = None
        if loci and i < len(loci) and loci[i]:
            locus_acc = locus_accessibility(loci[i][0], loci[i][1], cell_type) # REAL Stage B track (or None)
        acc = accessibility[i] if (accessibility and i < len(accessibility)) else None
        noms.append({"site": s, "n_mismatch": nmm, "empirical_active_fraction": af,
                     "risk_band": _risk_band(af), "crisot_score": crisot,
                     "crisot_source": ("cached_bench" if crisot is not None else "on-VM tool (not cached)"),
                     "chromatin": _chromatin_modifier(acc, locus_acc), "output_kind": "candidate"})
    # rank by the real CRISOT score when available, else by empirical risk (descending), then fewer mismatches
    noms.sort(key=lambda n: (n["crisot_score"] if n["crisot_score"] is not None else -1.0,
                             n["empirical_active_fraction"] or 0.0, -n["n_mismatch"]), reverse=True)
    return {"family": "nuclease", "available": True, "abstain": False, "guide": g20,
            "n_candidates": len(noms), "assay_calibration": assay,
            "nominations": noms[:top],
            "method": ("risk = empirical active fraction at k mismatches (real GUIDE-seq/CIRCLE-seq data); "
                       "ranked by the real CRISOT-Score when the (guide,site) is cached, else by empirical risk"),
            "bench": BENCH_SUMMARY.get(assay), "output_kind": "candidate",
            "honesty": "candidates, NOT a clearance, confirm with the recommended empirical assay"}


def pseudo_attb_sites(sequence: str, integrase: str = "Bxb1", max_arm_mismatch: int = 4, top: int = 20) -> dict:
    """Nominate cryptic **pseudo-attB** sites in a provided sequence for a serine integrase, seeding on the REAL
    documented attB core (e.g. Bxb1 GCGGTCTC / central GT) and tolerating arm mismatches. Candidate-flagged; the
    validating assay is Cryptic-seq/HIDE-seq. Abstains when no documented att core is bundled for the integrase."""
    from pen_stack.atlas.guide_design import _INTEGRASE_ATT
    att = _INTEGRASE_ATT.get(integrase)
    if not att:
        return {"family": "serine_integrase", "available": False, "abstain": True,
                "note": f"no documented att core bundled for {integrase!r}, cannot scan without fabricating"}
    core, attb = att["core"].upper(), att["attB"].upper()
    seq = (sequence or "").upper()
    L = len(attb)
    # locate the core within the full attB so we can align scanned windows to the documented site
    c0 = attb.find(core)
    hits = []
    idx = seq.find(core)
    while idx != -1:
        start = idx - c0
        if 0 <= start and start + L <= len(seq):
            window = seq[start:start + L]
            if "N" not in window:
                arm_mm = sum(1 for a, b in zip(window, attb) if a != b)
                if arm_mm <= max_arm_mismatch:
                    hits.append({"pos": start, "site": window, "arm_mismatch": arm_mm,
                                 "core_matched": True, "output_kind": "candidate"})
        idx = seq.find(core, idx + 1)
    hits.sort(key=lambda h: h["arm_mismatch"])
    return {"family": "serine_integrase", "integrase": integrase, "available": True, "abstain": False,
            "att_core": core, "n_candidates": len(hits), "nominations": hits[:top],
            "method": (f"cryptic pseudo-attB scan: seed on the documented {integrase} core {core} (central "
                       f"{att['central_dinucleotide']}), verify the {L}-nt attB with <= {max_arm_mismatch} arm "
                       "mismatches"),
            "validating_assay": "Cryptic-seq / HIDE-seq (Hazelbaker et al., bioRxiv 2024.08.23.609471)",
            "honesty": "CANDIDATE cryptic sites, recombination at a pseudo-attB is not claimed; confirm by "
                       "Cryptic-seq/HIDE-seq. Quantitative LSI off-target prediction (IntQuery) is paper-only "
                       "(no public weights), not run here."}


def nominate_offtargets(writer_family: str, guide: str | None = None, candidate_sites: list[str] | None = None,
                        sequence: str | None = None, accessibility: list[float] | None = None,
                        target_core: str | None = None, fasta=None, chroms: list[str] | None = None,
                        assay: str = "guideseq", loci: list | None = None, cell_type: str = "k562",
                        enzyme: str | None = None, max_mismatch: int = 5) -> dict:
    """Cross-family dispatcher. Returns a nomination dict (candidates, never claims) + the recommended validation
    assay, or an abstention. Never fabricates off-target sites. ``loci`` (per-candidate (chrom, bin)) +
    ``cell_type`` enable the REAL Stage B chromatin-accessibility modifier for nucleases.

    v7.2 (O-WS2): for a nuclease guide WITHOUT supplied ``candidate_sites``, this runs the genome-wide FINDER
    (enumerate GRCh38 -> CRISOT -> risk -> chromatin), the CRISPOR-like default. Supplying ``candidate_sites``
    keeps the v6.10 score-my-candidates path (backward compatible)."""
    from pen_stack.wgenome.offtarget_assay import recommend_assay
    fam = (writer_family or "").lower()
    assay_rec = recommend_assay(writer_family)
    # PASTE first (its name embeds an integrase) → compose nuclease + integrase (O-WS6)
    if fam in _PASTE or "paste" in fam or "passige" in fam:
        from pen_stack.wgenome.offtarget_paste import nominate_paste
        res = nominate_paste(guide=guide, integrase="Bxb1", max_mismatch=max_mismatch, assay=assay,
                             cell_type=cell_type)
    elif fam in _CAST or "cast" in fam or "cas12k" in fam:
        from pen_stack.wgenome.offtarget_cast import nominate_cast
        res = nominate_cast(system=enzyme or writer_family or "ShCAST", spacer=guide, max_mismatch=max_mismatch)
    elif fam in _NUCLEASE or "cas9" in fam or "nuclease" in fam:
        if candidate_sites:  # v6.10 path: score/rank the caller-supplied candidates
            res = nominate_nuclease(guide or "", candidate_sites, accessibility, assay, loci=loci,
                                    cell_type=cell_type)
        else:  # v7.2 finder: enumerate genome-wide, then score (replays the VM cache or abstains)
            from pen_stack.wgenome.offtarget_nuclease import find_nuclease_offtargets
            res = find_nuclease_offtargets(guide or "", enzyme=enzyme or writer_family or "SpCas9",
                                           max_mismatch=max_mismatch, assay=assay, cell_type=cell_type)
    elif fam in _INTEGRASE or "integrase" in fam or "bxb1" in fam or "phic31" in fam:
        integrase = "PhiC31" if "phic31" in fam else "Bxb1"
        if sequence:  # v6.10 path: scan a supplied locus for cryptic pseudo-attB
            res = pseudo_attb_sites(sequence, "Bxb1")
        else:  # v7.2 genome-wide pseudo-attP scan (O-WS3)
            from pen_stack.wgenome.offtarget_integrase import nominate_integrase
            res = nominate_integrase(integrase)
    elif fam in _BRIDGE or "bridge" in fam or "is110" in fam or "is621" in fam or "seek" in fam:
        from pen_stack.wgenome.offtarget_bridge import nominate_bridge
        res = nominate_bridge(target_core=target_core, writer_family=writer_family, fasta=fasta, chroms=chroms)
    else:
        res = {"family": writer_family, "available": False, "abstain": True,
               "note": f"no off-target nomination model for family {writer_family!r}"}
    res["recommended_assay"] = assay_rec
    res["nomination_is_not_clearance"] = True
    return res
