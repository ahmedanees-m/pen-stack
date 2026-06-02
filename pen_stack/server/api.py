"""PEN-STACK REST API (Phase 2, Step 2.6) — atlas + cross-link endpoints over FastAPI.

Extends the Phase-1 atlas with the Writer Atlas and the writer<->locus cross-link. Every quantitative
result is computed by the validated library functions (never guessed); the ``/ask`` route defers numeric
claims to those tools (Step 2.8). Heavy data is loaded lazily so the app boots without the Phase-1 atlas.

Run: ``uvicorn pen_stack.server.api:app --host 0.0.0.0 --port 8000`` (needs the ``server`` extra).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from fastapi import FastAPI, HTTPException, Query
except ImportError as e:  # pragma: no cover - server extra optional
    raise ImportError("FastAPI not installed: pip install 'pen-stack[server]'") from e

from pen_stack import __version__

_ATLAS = Path(__file__).resolve().parents[1] / "atlas" / "atlas.parquet"

app = FastAPI(title="PEN-STACK API", version=__version__,
              description="Open infrastructure for genome writing: Writer Atlas + Writable Genome cross-link.")

_DISCLAIMER = ("Decision-support only — predictions are calibrated risk/durability estimates, not "
               "clinical directives. Tier-2/3 reachability is candidate and requires experimental validation.")


def _atlas_df() -> pd.DataFrame:
    if not _ATLAS.exists():
        raise HTTPException(503, "atlas.parquet not built")
    return pd.read_parquet(_ATLAS)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "atlas_present": _ATLAS.exists()}


@app.get("/atlas/coverage")
def atlas_coverage():
    df = _atlas_df()
    cov = (df.groupby("family")
             .agg(n=("representative_system", "size"),
                  measured=("confidence", lambda s: int((s == "measured").sum())),
                  reachability_tier=("reachability_tier", "first"),
                  mechanism=("mechanism_bucket", "first"))
             .reset_index())
    return {"families": int(df["family"].nunique()), "systems": int(len(df)),
            "coverage": cov.to_dict("records"), "disclaimer": _DISCLAIMER}


@app.get("/atlas")
def atlas(family: str | None = None, limit: int = Query(50, le=500)):
    df = _atlas_df()
    if family:
        df = df[df["family"] == family]
    cols = [c for c in ["representative_system", "family", "confidence", "mechanism_bucket",
                        "deliv_class", "readiness", "cargo_capacity_bp", "reachability_tier",
                        "human_cell_activity"] if c in df.columns]
    return {"n": int(len(df)), "rows": df[cols].head(limit).to_dict("records"), "disclaimer": _DISCLAIMER}


@app.get("/crosslink/writers")
def crosslink_writers(chrom: str, bin: int, ct: str = "k562"):
    from pen_stack.atlas import crosslink as cl
    try:
        w = cl.writers_for_locus(chrom, bin, ct)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    if w.empty:
        return {"locus": f"{chrom}:bin{bin}", "writers": [], "disclaimer": _DISCLAIMER}
    fams = w.groupby("family").size().to_dict()
    return {"locus": f"{chrom}:bin{bin}", "ct": ct,
            "locus_writability": float(w["locus_writability"].iloc[0]),
            "families": {k: int(v) for k, v in fams.items()},
            "n_systems": int(len(w)), "disclaimer": _DISCLAIMER}


@app.get("/crosslink/loci")
def crosslink_loci(family: str, ct: str = "k562", top: int = Query(20, le=200)):
    from pen_stack.atlas import crosslink as cl
    try:
        loci = cl.loci_for_writer(family, ct, top=top)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    return {"family": family, "ct": ct, "loci": loci.to_dict("records"), "disclaimer": _DISCLAIMER}


@app.get("/writable")
def writable(gene: str, ct: str = "k562", top: int = Query(20, le=200)):
    from pen_stack.atlas.crosslink import loci_for_gene
    try:
        g = loci_for_gene(gene, ct)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    if g.empty:
        return {"gene": gene, "ct": ct, "loci": [], "disclaimer": _DISCLAIMER}
    cols = ["chrom", "bin", "safety", "p_durable", "writability"]
    return {"gene": gene, "ct": ct, "loci": g[cols].head(top).to_dict("records"), "disclaimer": _DISCLAIMER}


@app.get("/ask")
def ask(q: str):
    """Grounded, cited Q&A (Step 2.8). Numeric claims are resolved by tool calls, never guessed."""
    from pen_stack.rag.qa import answer
    return answer(q)


@app.get("/plan")
def plan(gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562", k: int = Query(5, le=20)):
    """Write Planner (Step 3.4): goal + edit_intent -> ranked, traceable plans."""
    from pen_stack.planner.optimize import EditIntent
    from pen_stack.planner.pipeline import plan_write
    try:
        intent_e = EditIntent(intent)
    except ValueError as e:
        raise HTTPException(422, f"unknown edit_intent: {intent}") from e
    try:
        plans = plan_write(gene, intent_e, cargo_bp, ct, k=k)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    return {"gene": gene, "intent": intent, "ct": ct, "n": len(plans), "plans": plans,
            "disclaimer": _DISCLAIMER}
