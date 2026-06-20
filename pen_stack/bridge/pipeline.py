"""pen-bridge: design + assess a bridge-RNA (Phase 1.5, Step 1.5.5).

WRAPS the authoritative Arc BridgeRNADesigner (``bridgernadesigner``) - does not reimplement it - and adds
the PEN-STACK layer on top: genome-wide off-target prediction (1.5.2), fold + cross-loop QC (1.5.3), and
optional overlay with the Phase-1 safety layer (is an off-target in a dangerous locus?).

Graceful: if ``bridgernadesigner`` is absent, off-target + cross-loop still run on the user-supplied
target/donor cores; only the full scaffold sequence (for ViennaRNA folding) needs the designer.
"""
from __future__ import annotations

from pathlib import Path

from pen_stack.bridge.fold_qc import qc_verdict
from pen_stack.bridge.offtarget import scan_offtargets

# default hg38 locations (VM); overridable
_HG38_CANDIDATES = [
    Path.home() / "cast-bench" / "data" / "external" / "genomes" / "hg38.fa",
    Path("/work/data/external/genomes/hg38.fa"),
    Path("data/external/genomes/hg38.fa"),
]


def _hg38() -> Path | None:
    import os
    env = os.environ.get("PEN_HG38")
    if env and Path(env).exists():
        return Path(env)
    return next((p for p in _HG38_CANDIDATES if p.exists()), None)


def design_brna(target: str, donor: str, scaffold: str = "ISCro4_enhanced") -> dict:
    """Call the wrapped Arc designer. Returns the bridge sequence + cores, or a graceful note."""
    try:
        from bridgernadesigner.run import design_bridge_rna
    except Exception as e: # noqa: BLE001
        return {"available": False, "target": target.upper(), "donor": donor.upper(),
                "scaffold": scaffold, "note": f"bridgernadesigner not installed ({e}); pip install bridgernadesigner"}
    brna = design_bridge_rna(target, donor, scaffold)
    return {"available": True, "scaffold": scaffold, "target": brna.target, "donor": brna.donor,
            "bridge_sequence": brna.bridge_sequence}


def design_and_assess(target: str, donor: str, scaffold: str = "ISCro4_enhanced",
                      chroms: list[str] | None = None, fasta: str | Path | None = None,
                      ct: str | None = None, scan: bool = True) -> dict:
    """End-to-end: design (wrapped) -> off-target + fold/cross-loop QC -> optional safety overlay."""
    brna = design_brna(target, donor, scaffold)
    tcore, dcore = brna["target"], brna["donor"]

    qc = qc_verdict(tcore, dcore, brna.get("bridge_sequence"))

    off = {"scanned": False}
    if scan:
        fa = Path(fasta) if fasta else _hg38()
        if fa and fa.exists():
            chroms = chroms or [f"chr{i}" for i in range(1, 23)] + ["chrX"]
            df = scan_offtargets(fa, tcore, chroms)
            if ct is not None:
                df = annotate_with_safety(df, ct)
            off = {"scanned": True, "n_candidates": int(len(df)),
                   "n_exact": int((df["n_mm"] == 0).sum()) if not df.empty else 0,
                   "table": df}
        else:
            off = {"scanned": False, "note": "hg38 fasta not found; set PEN_HG38 or pass fasta="}

    return {"brna": brna, "offtargets": off, "qc": qc,
            "disclaimer": "Decision-support only; predicted off-targets require experimental validation."}


def annotate_with_safety(off_df, ct: str):
    """Overlay each off-target with the Phase-1 safety score (is the off-target in a dangerous locus?)."""
    if off_df.empty:
        return off_df
    try:
        from pen_stack.atlas.crosslink import load_writability
        wdf = load_writability(ct)[["chrom", "bin", "safety"]]
        out = off_df.copy()
        out["bin"] = (out["pos"] // 1000).astype(int)
        return out.merge(wdf, on=["chrom", "bin"], how="left")
    except Exception: # noqa: BLE001 - safety overlay is optional
        return off_df
