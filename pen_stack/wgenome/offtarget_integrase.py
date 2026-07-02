"""Serine-integrase pseudo-att genome scan (PEN-OFFTGT v2, O-WS3; sealed-benchmarked in v7.2.1).

A serine integrase recombines a donor attB with genomic **pseudo-attP** sites resembling the phage attP. This
enumerates pseudo-attP genome-wide: a fixed-sequence Cas-OFFinder scan of the attP core window over GRCh38 (heavy;
runs on the VM, replayed from cache here), scored by att-arm similarity.

**Honest status (v7.2.1): mechanism-based, with a SEALED NEGATIVE recall benchmark.** Bxb1 and PhiC31 att are
independently verified (Bxb1: FlyBase FBto0000359 / Ghosh 2003; PhiC31: PDB 9U2T/9U2S + Groth 2000), and the
PhiC31 human pseudo-attP set is verified (Thyagarajan 2001, GenBank AF333429/30/31). But a sealed recall benchmark
on those documented pseudosites is **NEGATIVE** — att-sequence-similarity does not recover them above random
background (all three at the background median). So the genome-wide pseudo-attP SIMILARITY RANKING is a
mechanism-based scan that is **not validated** as a predictor (φC31 recognition needs palindrome architecture /
a learned model, not raw identity). The documented pseudosites are surfaced as verified known-off-target loci.
Confirming assay: Cryptic-seq / HIDE-seq. Never fabricates sites or a validated status.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack.wgenome.offtarget_enumerate import enumerate_motif

_STATUS = "mechanism_based_unvalidated"  # the similarity ranking; sealed PhiC31 recall benchmark is NEGATIVE
_ALIAS = {"bxb1": "Bxb1", "serine_integrase": "Bxb1", "pe_integrase": "Bxb1",
          "phic31": "PhiC31", "phic31_integrase": "PhiC31"}
_CONFIRM = "Cryptic-seq / HIDE-seq (Tome Biosciences, 2024 preprint)"


@lru_cache(maxsize=1)
def integrase_att() -> dict:
    try:
        import yaml

        from pen_stack._resources import resource
        return yaml.safe_load(resource("data/curated/integrase_att.yaml").read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def resolve_integrase(name: str) -> str | None:
    n = (name or "").strip()
    if n in (integrase_att().get("integrases") or {}):
        return n
    return _ALIAS.get(n.lower())


def _sealed_benchmark() -> dict | None:
    return ((integrase_att().get("integrases") or {}).get("PhiC31") or {}).get("recall_benchmark")


def nominate_integrase(integrase: str = "Bxb1", top: int = 20) -> dict:
    """Genome-wide pseudo-attP nomination for a serine integrase. PhiC31 returns its verified documented human
    pseudo-attP (ψA/ψC/ψD) plus the sealed recall benchmark (NEGATIVE, verbatim). Bxb1 (and any integrase with a
    committed genome-scan cache) returns genome-wide similarity candidates carrying the same unvalidated-ranking
    caveat. Never fabricates sites or a validated status."""
    att = integrase_att()
    key = resolve_integrase(integrase)
    bench = _sealed_benchmark()
    if key is None or key not in (att.get("integrases") or {}):
        return {"family": "serine_integrase", "integrase": integrase, "available": False, "abstain": True,
                "status": _STATUS, "note": f"no encoded att for integrase {integrase!r}; encoded: "
                f"{sorted((att.get('integrases') or {}))}", "confirm_assay": _CONFIRM,
                "nomination_is_not_clearance": True}
    rec = att["integrases"][key]

    if key == "PhiC31":
        # promiscuous integrase: surface the VERIFIED documented pseudo-attP + the sealed NEGATIVE recall benchmark
        return {"family": "serine_integrase", "integrase": "PhiC31", "available": True, "abstain": False,
                "status": _STATUS, "att_core": rec["core"], "central_dinucleotide": rec["central_dinucleotide"],
                "att_doi": rec["doi"], "pdb": rec.get("pdb"),
                "documented_pseudo_attP": rec.get("pseudo_attP_positive_set"),
                "documented_source": rec.get("positive_set_source"), "documented_doi": rec.get("positive_set_doi"),
                "sealed_recall_benchmark": bench, "similarity_ranking_validated": False,
                "specificity_note": rec.get("specificity_note"),
                "method": ("PhiC31 documented human pseudo-attP (verified GenBank AF333429/30/31, Thyagarajan 2001) "
                           "are surfaced as known off-target loci; the att-similarity genome scan is mechanism-"
                           "based and its SEALED recall benchmark is NEGATIVE (does not recover them above "
                           "background) -> the genome-wide ranking is unvalidated (reported verbatim)."),
                "confirm_assay": _CONFIRM,
                "honesty": "verified documented pseudosites + an honest NEGATIVE recall benchmark; NOT a validated "
                           "predictor and NOT a clearance.",
                "nomination_is_not_clearance": True}

    # Bxb1 (and any integrase with a committed genome-scan cache): genome-wide similarity candidates
    window = rec["scan_window"]
    enum = enumerate_motif(f"{key}_pseudo_attP")
    if enum.get("abstain"):
        return {"family": "serine_integrase", "integrase": key, "available": False, "abstain": True,
                "status": _STATUS, "att_core": rec["core"], "note": enum["note"],
                "cached_motifs": enum.get("cached_motifs", []), "sealed_recall_benchmark": bench,
                "confirm_assay": _CONFIRM, "nomination_is_not_clearance": True}
    wlen = len(window)
    noms = []
    for s in enum["sites"]:
        nmm = int(s["n_mismatch"])
        noms.append({"chrom": s["chrom"], "position": s["position"], "strand": s["strand"], "site": s["sequence"],
                     "n_mismatch": nmm, "arm_similarity": round(1.0 - nmm / wlen, 3), "output_kind": "candidate"})
    noms.sort(key=lambda n: n["n_mismatch"])
    return {"family": "serine_integrase", "integrase": key, "available": True, "abstain": False, "mode": "finder",
            "status": _STATUS, "att_core": rec["core"], "central_dinucleotide": rec["central_dinucleotide"],
            "scan_window": window, "source": enum["source"], "att_doi": rec["doi"],
            "n_sites_genome_wide": len(noms), "nominations": noms[:top],
            "specificity_note": rec.get("specificity_note"),
            "sealed_recall_benchmark": bench, "similarity_ranking_validated": False,
            "method": ("fixed-sequence Cas-OFFinder scan of the attP core window over GRCh38, scored by att-arm "
                       "similarity. The similarity RANKING is mechanism-based and UNVALIDATED: the sealed PhiC31 "
                       "recall benchmark is NEGATIVE (att-similarity does not recover documented pseudo-attP "
                       "above background)."),
            "confirm_assay": _CONFIRM,
            "honesty": "genome-wide pseudo-attP candidates by att similarity; the ranking is unvalidated "
                       "(sealed-negative benchmark) and NOT a clearance.",
            "nomination_is_not_clearance": True}
