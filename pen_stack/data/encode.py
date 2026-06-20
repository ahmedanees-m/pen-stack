"""ENCODE REST resolver (Phase 1, Step 1.1).

Resolves released hg38 bigWig SIGNAL files for a (biosample, assay/target) pair via the ENCODE
Portal REST API - so we never hard-code possibly-wrong file accessions. Returns accession + href.
"""
from __future__ import annotations

import requests

ENCODE = "https://www.encodeproject.org"
HEADERS = {"accept": "application/json"}

# preferred processed signal output per assay (fold-change over control where available)
_PREF_OUTPUT = [
    "fold change over control",
    "signal p-value",
    "read-depth normalized signal",
    "signal",
]


def _search(params: dict) -> list[dict]:
    r = requests.get(f"{ENCODE}/search/", params=params, headers=HEADERS, timeout=60)
    if r.status_code == 404:
        return [] # ENCODE returns 404 for zero-result searches with some param combos
    r.raise_for_status()
    return r.json().get("@graph", [])


def find_bigwig(biosample: str, assay_title: str, target: str | None = None,
                assembly: str = "GRCh38") -> dict | None:
    """Find one released bigWig signal file for a biosample + assay (+ histone target).

    biosample e.g. 'K562'; assay_title e.g. 'Histone ChIP-seq' / 'ATAC-seq' / 'DNase-seq';
    target e.g. 'H3K27ac' (None for ATAC/DNase).
    """
    params = {
        "type": "File",
        "file_format": "bigWig",
        "output_type": _PREF_OUTPUT,
        "assembly": assembly,
        "status": "released",
        "biosample_ontology.term_name": biosample,
        "assay_title": assay_title,
        "format": "json",
        "limit": "50",
    }
    if target:
        params["target.label"] = target
    files = _search(params)
    if not files:
        return None
    # rank by preferred output_type order, prefer non-isogenic-replicate consensus where present
    def rank(f):
        ot = f.get("output_type", "")
        return _PREF_OUTPUT.index(ot) if ot in _PREF_OUTPUT else len(_PREF_OUTPUT)
    f = sorted(files, key=rank)[0]
    return {"accession": f["accession"], "href": ENCODE + f["href"],
            "output_type": f.get("output_type"), "assembly": assembly,
            "biosample": biosample, "assay": assay_title, "target": target}


# default track panel per the prereg (durability features)
DEFAULT_PANEL = [
    ("ATAC-seq", None),
    ("DNase-seq", None),
    ("Histone ChIP-seq", "H3K27ac"),
    ("Histone ChIP-seq", "H3K4me1"),
    ("Histone ChIP-seq", "H3K4me3"),
    ("Histone ChIP-seq", "H3K9me3"),
    ("Histone ChIP-seq", "H3K27me3"),
]


def resolve_panel(biosample: str, panel=DEFAULT_PANEL, assembly: str = "GRCh38") -> dict[str, dict]:
    """Return {track_name: file_record} for the panel, skipping assays with no released bigWig.
    Partial panels are returned as-is (e.g. a cell type lacking some histone marks) - graceful."""
    out = {}
    for assay, target in panel:
        rec = find_bigwig(biosample, assay, target, assembly=assembly)
        name = target or assay.split("-")[0].lower() # H3K27ac / atac / dnase
        if rec:
            out[name] = rec
    return out
