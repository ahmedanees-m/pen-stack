"""PEN-STACK REST API (Phase 2, Step 2.6) - atlas + cross-link endpoints over FastAPI.

Extends the Phase-1 atlas with the Writer Atlas and the writer<->locus cross-link. Every quantitative
result is computed by the validated library functions (never guessed); the ``/ask`` route defers numeric
claims to those tools (Step 2.8). Heavy data is loaded lazily so the app boots without the Phase-1 atlas.

Run: ``uvicorn pen_stack.server.api:app --host 0.0.0.0 --port 8000`` (needs the ``server`` extra).
"""
from __future__ import annotations

import json
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

_DISCLAIMER = ("Decision-support only - predictions are calibrated risk/durability estimates, not "
               "clinical directives. Tier-2/3 reachability is candidate and requires experimental validation.")


def _atlas_df() -> pd.DataFrame:
    if not _ATLAS.exists():
        raise HTTPException(503, "atlas.parquet not built")
    return pd.read_parquet(_ATLAS)


def _records(df: pd.DataFrame) -> list[dict]:
    """JSON-safe records from a DataFrame: NaN/inf -> null and numpy scalars -> native (pandas `to_json`
    handles both). Raw `to_dict('records')` leaks non-finite floats, which the JSON encoder rejects (500)."""
    return json.loads(df.to_json(orient="records"))


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
    return {"n": int(len(df)), "rows": _records(df[cols].head(limit)), "disclaimer": _DISCLAIMER}


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
    return {"family": family, "ct": ct, "loci": _records(loci), "disclaimer": _DISCLAIMER}


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
    return {"gene": gene, "ct": ct, "loci": _records(g[cols].head(top)), "disclaimer": _DISCLAIMER}


@app.get("/bridge/design")
def bridge_design(target: str, donor: str, scaffold: str = "ISCro4_enhanced",
                  ct: str | None = None, scan: bool = False):
    """Bridge-recombinase design + off-target/QC (Phase 1.5). scan=false by default (genome scan is heavy)."""
    from pen_stack.bridge.pipeline import design_and_assess
    res = design_and_assess(target, donor, scaffold, ct=ct, scan=scan)
    off = res["offtargets"]
    if off.get("scanned") and "table" in off:
        t = off["table"]
        off = {"scanned": True, "n_candidates": off["n_candidates"], "n_exact": off["n_exact"],
               "top": t.head(20).to_dict("records")}
    return {"brna": {k: v for k, v in res["brna"].items() if k != "bridge_sequence"} |
            ({"bridge_sequence_len": len(res["brna"]["bridge_sequence"])} if res["brna"].get("available") else {}),
            "qc": res["qc"], "offtargets": off, "disclaimer": res["disclaimer"]}


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


@app.post("/verify")
def verify_endpoint(design: dict):
    """v3.3 verification service (WS-V): submit a proposed genomic write, get back a structured Verdict —
    legality + named rejections + calibrated confidence + epistemic status + scope flags. Legality and
    confidence are distinct axes. A `question` key (optional) is checked against the known-unknowns registry."""
    from pen_stack.verify import verify
    return verify(design).model_dump()


@app.post("/graph/query")
def graph_query_endpoint(q: dict):
    """v4.5 world-model graph (WS-G): multi-hop query. Body: {locus, cargo_form?}. Returns writers that
    reach the locus AND are deliverable by a cargo-form-compatible vehicle, each with its provenanced path."""
    from pen_stack.graph import writers_reaching_and_deliverable
    return writers_reaching_and_deliverable(q.get("locus"), cargo_form=q.get("cargo_form"))


# ======================================================================================
# v6.1 — The AI Integration Surface: the self-describing contract + the engine tool routes.
# An external agent fetches /capabilities + /scope and ROUTES on them, then calls the tools.
# ======================================================================================
@app.get("/capabilities", tags=["v6.1 AI surface"])
def capabilities_endpoint():
    """Machine-readable: WHAT PEN-STACK can do (tools, inputs, outputs, stability). Route on this, not prose."""
    from pen_stack.api.manifest import capability_manifest
    return capability_manifest()


@app.get("/scope", tags=["v6.1 AI surface"])
def scope_endpoint():
    """Machine-readable: WHAT PEN-STACK REFUSES to answer (known-unknowns + oracle scope cards). The contract
    that makes depending on PEN-STACK safe: outputs outside scope are out_of_scope/extrapolating, never asserted."""
    from pen_stack.api.manifest import scope_manifest
    return scope_manifest()


@app.post("/safety", tags=["v6.1 AI surface"])
def safety_endpoint(design: dict):
    """v5.7 Guardian: biosecurity / dual-use screen -> SafetyVerdict (clear/flag/escalate/refuse) + reason."""
    from pen_stack.safety import safety_gate
    return safety_gate(design, actor=str(design.get("actor", "api"))).model_dump()


@app.post("/immune", tags=["v6.1 AI surface"])
def immune_endpoint(design: dict):
    """v5.6 immune-risk profile: per-axis screen (never collapsed; collapsed_score is None)."""
    from pen_stack.planner.immune_profile import immune_profile
    return immune_profile(design)


@app.post("/generate", tags=["v6.1 AI surface"])
def generate_endpoint(req: dict):
    """v5.8 generative designer: verifier-as-discriminator. Body: {goal?, candidates?, keep?}. Hazardous/illegal
    candidates are discarded; survivors are calibrated + immune-profiled candidates (never asserted to work)."""
    from pen_stack.design import generate_designs
    return {"survivors": generate_designs(req.get("goal"), candidates=req.get("candidates"),
                                          keep=int(req.get("keep", 25)), actor=str(req.get("actor", "api"))),
            "disclaimer": _DISCLAIMER}


@app.post("/predict", tags=["v6.1 AI surface"])
def predict_endpoint(req: dict):
    """v5.9 digital twin: calibrated, OOD-gated, phenotype-bounded outcome. Body: {design, cell_state}."""
    from pen_stack.twin import predict_outcome
    return predict_outcome(req["design"], req.get("cell_state", "k562"))


@app.post("/suggest", tags=["v6.1 AI surface"])
def suggest_endpoint(req: dict):
    """v5.10 experiment designer: a diverse, informative next-experiment batch. Body: {candidates, cell_state, k?}."""
    from pen_stack.active import select_batch
    return {"batch": select_batch(req["candidates"], req.get("cell_state", "k562"), {},
                                  k=int(req.get("k", 8))), "disclaimer": _DISCLAIMER}


@app.post("/session", tags=["v6.1 AI surface"])
def session_endpoint(req: dict):
    """v5.13 co-scientist: drive the full loop. Body: {goal, cell_state, candidates?}. Returns strategies +
    predicted outcomes + per-axis immune profiles + suggested experiments + citations + scope ledger + safety."""
    from pen_stack.agent.co_scientist import co_scientist_session
    return co_scientist_session(req["goal"], req.get("cell_state", "k562"), candidates=req.get("candidates"))


# ======================================================================================
# v5.13 — The Genome-Writing Challenge (read-only surface for the web Challenge page).
# Public tasks (NO labels) + the PEN-STACK reference submission that anchors the leaderboard. Submissions
# are Python `predict_fn`s scored offline (`benchmarks/genome_writing_challenge/run.py`) — never accepted
# over HTTP — so these routes only EXPOSE the held-out round and the anchor score.
# ======================================================================================
@app.get("/challenge/tasks", tags=["challenge"])
def challenge_tasks(round_id: str = "2026R1"):
    """The public inputs of the current held-out round (family + design + instructions; NEVER the label)."""
    from benchmarks.genome_writing_challenge.harness import _round_tasks
    tasks = _round_tasks(round_id)
    return {"round": round_id, "n_tasks": len(tasks),
            "tasks": [{"id": t.id, "family": t.family, "public_input": t.public_input} for t in tasks]}


@app.get("/challenge/leaderboard", tags=["challenge"])
def challenge_leaderboard(round_id: str = "2026R1"):
    """The leaderboard anchored by the PEN-STACK reference submission (deterministic, non-circular labels,
    no-fabrication audited). External submissions are scored offline and appended here after a round."""
    from benchmarks.genome_writing_challenge.harness import evaluate, reference_submission
    ref = evaluate(reference_submission(), round_id)
    return {"round": round_id, "leaderboard": [ref],
            "rules": {"no_circular_labels": ref["no_circular_labels"],
                      "no_fabrication_audited": True, "labels": "validated PEN-STACK verifier / oracles"}}
