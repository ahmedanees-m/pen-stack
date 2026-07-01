"""Serine-integrase pseudo-att genome scan (PEN-OFFTGT v2, O-WS3).

A serine integrase recombines a donor attB with genomic **pseudo-attP** sites resembling the phage attP. This
enumerates pseudo-attP genome-wide: a fixed-sequence Cas-OFFinder scan of the attP core window over GRCh38 (heavy;
runs on the VM, replayed from cache here), scored by att-arm similarity (mismatch to the documented att) and
overlaid with the known-specificity note.

Status: **semi_validated** — documented pseudosites are partial ground truth, but no CRISPOR-scale validated
predictor exists for integrases. Bxb1 is fully encoded (FlyBase FBto0000359 / Ghosh 2003) and is highly specific;
**PhiC31 is a DISCLOSED data gap** (its human pseudo-attP set is documented — Chalberg 2006 — but its exact att
arm / pseudosite sequences were not verifiable from an open source in this build, so it abstains rather than
fabricate). Confirming assay: Cryptic-seq / HIDE-seq. Never fabricates sites or a validated status.
"""
from __future__ import annotations

from functools import lru_cache

from pen_stack.wgenome.offtarget_enumerate import enumerate_motif

_STATUS = "semi_validated"
_ALIAS = {"bxb1": "Bxb1", "serine_integrase": "Bxb1", "pe_integrase": "Bxb1", "paste": "Bxb1",
          "passige": "Bxb1", "phic31": "PhiC31", "phic31_integrase": "PhiC31"}


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


def nominate_integrase(integrase: str = "Bxb1", top: int = 20) -> dict:
    """Genome-wide pseudo-attP nomination for a serine integrase. Replays the cached VM scan of the attP core
    window, scores by att-arm similarity, and ranks by fewer mismatches (more att-like = higher recombination
    risk). Abstains with a disclosure for an integrase without an encoded att (e.g. PhiC31). Never fabricates."""
    att = integrase_att()
    key = resolve_integrase(integrase)
    if key is None or key not in (att.get("integrases") or {}):
        disc = att.get("phic31_disclosure", {})
        if (integrase or "").lower().startswith("phic31"):
            return {"family": "serine_integrase", "integrase": "PhiC31", "available": False, "abstain": True,
                    "status": _STATUS, "note": "PhiC31 att / pseudo-attP not encoded (disclosed data gap): "
                    f"{disc.get('documented_fact', '')}", "disclosure": disc,
                    "confirm_assay": "Cryptic-seq / HIDE-seq", "nomination_is_not_clearance": True}
        return {"family": "serine_integrase", "integrase": integrase, "available": False, "abstain": True,
                "status": _STATUS, "note": f"no encoded att for integrase {integrase!r}; encoded: "
                f"{sorted((att.get('integrases') or {}))}"}

    rec = att["integrases"][key]
    window = rec["scan_window"]
    enum = enumerate_motif(f"{key}_pseudo_attP")
    if enum.get("abstain"):
        return {"family": "serine_integrase", "integrase": key, "available": False, "abstain": True,
                "status": _STATUS, "att_core": rec["core"], "note": enum["note"],
                "cached_motifs": enum.get("cached_motifs", []), "confirm_assay": "Cryptic-seq / HIDE-seq",
                "nomination_is_not_clearance": True}

    wlen = len(window)
    noms = []
    for s in enum["sites"]:
        nmm = int(s["n_mismatch"])
        noms.append({"chrom": s["chrom"], "position": s["position"], "strand": s["strand"], "site": s["sequence"],
                     "n_mismatch": nmm, "arm_similarity": round(1.0 - nmm / wlen, 3), "output_kind": "candidate"})
    noms.sort(key=lambda n: n["n_mismatch"])
    n_exact = sum(1 for n in noms if n["n_mismatch"] == 0)
    return {"family": "serine_integrase", "integrase": key, "available": True, "abstain": False, "mode": "finder",
            "status": _STATUS, "att_core": rec["core"], "central_dinucleotide": rec["central_dinucleotide"],
            "scan_window": window, "source": enum["source"], "att_doi": rec["doi"],
            "n_sites_genome_wide": len(noms), "n_exact_att_window": n_exact, "nominations": noms[:top],
            "specificity_note": rec.get("specificity_note"),
            "method": ("fixed-sequence Cas-OFFinder scan of the attP core window over GRCh38, scored by att-arm "
                       "similarity (mismatch to the documented att); semi-validated (documented pseudosites are "
                       "partial ground truth; no CRISPOR-scale validated integrase predictor exists)"),
            "confirm_assay": "Cryptic-seq / HIDE-seq (Tome Biosciences, 2024 preprint)",
            "honesty": "genome-wide pseudo-attP CANDIDATES by att similarity; NOT a clearance and NOT a validated "
                       "predictor. Confirm by Cryptic-seq/HIDE-seq.",
            "nomination_is_not_clearance": True}
