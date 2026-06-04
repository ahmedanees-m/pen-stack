"""Cargo Polish - cargo-sequence durability-risk scan (v3.1, WS-D).

The locus model scores WHERE to write; this scores WHAT is written. It scans the insert (the user's
cassette sequence) for known sequence triggers of transgene silencing/instability and emits a
`cargo_durability_risk` score in [0,1] with a band and, for every flag, a concrete remedy.

This is a HEURISTIC flag, not a supervised silencing predictor: it catches documented sequence triggers
(CpG-island density -> de novo methylation; GC extremes; cryptic splice consensus; strong mRNA secondary
structure; known silencer motifs), not all silencing causes. Thresholds are documented constants
(configs/cargo_polish.yaml) from the silencing literature. ViennaRNA (MFE) is optional and degrades
gracefully (the structure term is skipped, noted) so the scan runs anywhere; the other terms are pure-Python.

Acceptance (prereg/ws_d.yaml): reproduces established directionality - high-CpG bacterial-style cassettes
score above CpG-depleted / insulator-flanked constructs on a small curated set - and every flag carries a
concrete suggestion.
"""
from __future__ import annotations

import re
from functools import lru_cache

import yaml


@lru_cache(maxsize=1)
def _cfg() -> dict:
    from pen_stack._resources import resource
    return yaml.safe_load(resource("configs/cargo_polish.yaml").read_text(encoding="utf-8"))


def _clean(seq: str) -> str:
    return re.sub(r"[^ACGT]", "", (seq or "").upper())


def gc_fraction(seq: str) -> float:
    s = _clean(seq)
    return (s.count("G") + s.count("C")) / len(s) if s else 0.0


def cpg_islands(seq: str) -> list[dict]:
    """Gardiner-Garden & Frommer sliding window: obs/exp CpG > threshold AND GC > threshold over the window."""
    c = _cfg()["cpg_island"]
    s = _clean(seq)
    w, step = c["window_bp"], max(1, c["window_bp"] // 4)
    out = []
    for i in range(0, max(1, len(s) - w + 1), step):
        win = s[i:i + w]
        if len(win) < w:
            break
        nC, nG = win.count("C"), win.count("G")
        gc = (nC + nG) / w
        exp = (nC * nG) / w if nC and nG else 0.0
        obs_exp = (win.count("CG") / exp) if exp else 0.0
        if obs_exp > c["obs_exp_min"] and gc > c["gc_min"]:
            out.append({"start": i, "obs_exp": round(obs_exp, 3), "gc": round(gc, 3)})
    # merge overlapping windows into island count
    merged, last_end = 0, -1
    for isl in out:
        if isl["start"] > last_end:
            merged += 1
        last_end = isl["start"] + w
    return [{"n_islands": merged, "windows": out}] if merged else []


def cryptic_splice_sites(seq: str) -> dict:
    c = _cfg()["cryptic_splice"]
    s = _clean(seq)
    donors = len(re.findall(c["donor_motif"], s))
    acceptors = len(re.findall(c["acceptor_motif"], s))
    return {"donor": donors, "acceptor": acceptors, "total": donors + acceptors}


def silencer_motifs(seq: str) -> list[dict]:
    s = _clean(seq)
    hits = []
    for m in _cfg()["silencer_motifs"]["motifs"]:
        n = len(re.findall(m["pattern"], s))
        if n:
            hits.append({"name": m["name"], "count": n, "note": m["note"]})
    return hits


def mfe_per_nt(seq: str) -> dict:
    """ViennaRNA minimum-free-energy per nucleotide of the transcribed insert; graceful if RNA is absent."""
    s = _clean(seq)
    if len(s) < 10:
        return {"available": False, "note": "sequence too short"}
    try:
        import RNA
    except Exception:  # noqa: BLE001 - ViennaRNA only in the bio extra / VM image
        return {"available": False, "note": "ViennaRNA not installed (bio extra / VM image)"}
    fc = RNA.fold_compound(s.replace("T", "U"))
    _struct, mfe = fc.mfe()
    return {"available": True, "mfe": round(float(mfe), 2), "mfe_per_nt": round(float(mfe) / len(s), 4)}


def scan_cargo(seq: str) -> dict:
    """Aggregate the cargo durability-risk scan: score in [0,1], band, and per-flag concrete suggestions."""
    cfg = _cfg()
    s = _clean(seq)
    flags, risk = [], 0.0
    sug = cfg["suggestions"]

    isl = cpg_islands(s)
    if isl:
        n = isl[0]["n_islands"]
        risk += min(0.5, n * cfg["cpg_island"]["risk_per_island"])
        flags.append({"category": "cpg_island", "detail": f"{n} CpG island(s)", "suggestion": sug["cpg_island"]})

    gc = gc_fraction(s)
    if gc and (gc < cfg["gc_extremes"]["gc_low"] or gc > cfg["gc_extremes"]["gc_high"]):
        risk += cfg["gc_extremes"]["risk"]
        flags.append({"category": "gc_extremes", "detail": f"GC={gc:.2f}", "suggestion": sug["gc_extremes"]})

    cs = cryptic_splice_sites(s)
    if cs["total"]:
        risk += min(cfg["cryptic_splice"]["risk_per_site_capped"], 0.05 * cs["total"])
        flags.append({"category": "cryptic_splice", "detail": f"{cs['total']} splice consensus site(s)",
                      "suggestion": sug["cryptic_splice"]})

    sm = silencer_motifs(s)
    if sm:
        risk += min(cfg["silencer_motifs"]["risk_per_motif_capped"], 0.07 * sum(h["count"] for h in sm))
        flags.append({"category": "silencer_motifs", "detail": ", ".join(h["name"] for h in sm),
                      "suggestion": sug["silencer_motifs"]})

    mfe = mfe_per_nt(s)
    if mfe.get("available") and mfe["mfe_per_nt"] < cfg["secondary_structure"]["mfe_per_nt_warn"]:
        risk += cfg["secondary_structure"]["risk"]
        flags.append({"category": "secondary_structure", "detail": f"MFE/nt={mfe['mfe_per_nt']}",
                      "suggestion": sug["secondary_structure"]})

    risk = round(min(1.0, risk), 4)
    b = cfg["bands"]
    band = "low" if risk < b["low"] else ("moderate" if risk < b["moderate"] else "high")
    return {"cargo_durability_risk": risk, "band": band, "length_bp": len(s),
            "gc": round(gc, 4), "n_flags": len(flags), "flags": flags,
            "components": {"cpg_islands": isl, "cryptic_splice": cs, "silencer_motifs": sm,
                           "secondary_structure": mfe},
            "scope": "heuristic sequence-trigger scan, not a supervised silencing predictor"}


if __name__ == "__main__":  # pragma: no cover
    import json
    demo = "CGCGCGCGGCGGCGCGCGGCGGCGCGCGGCGGCGCG" * 8
    print(json.dumps(scan_cargo(demo), indent=2, default=str))
