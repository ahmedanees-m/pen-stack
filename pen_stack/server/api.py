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
    from fastapi import FastAPI, HTTPException, Query, Request
except ImportError as e: # pragma: no cover - server extra optional
    raise ImportError("FastAPI not installed: pip install 'pen-stack[server]'") from e

from pen_stack import __version__

_ATLAS = Path(__file__).resolve().parents[1] / "atlas" / "atlas.parquet"

app = FastAPI(title="PEN-STACK API", version=__version__,
              description="Open infrastructure for genome writing: Writer Atlas + Writable Genome cross-link.")

_DISCLAIMER = ("Decision-support only - predictions are calibrated risk/durability estimates, not "
               "clinical directives. Tier-2/3 reachability is candidate and requires experimental validation.")


def _resolve_ct(request: Request, ct: str, cell_type: str | None, allowed_params: set[str]) -> str:
    """Resolve the cell type from `ct` OR its `cell_type` alias, and REJECT any unrecognized query parameter.

    Without this, a misnamed cell-type argument (e.g. `?cell_type=hspc` when the endpoint reads `ct`) is silently
    ignored by FastAPI and `ct` falls back to its "k562" default, so the caller gets confidently-wrong K562 data
    labelled coverage=full. We instead accept both names and 422 on any unknown parameter, so the fallback can
    never happen silently. The resolved cell type is validated against the known universe.
    """
    extra = set(request.query_params) - allowed_params
    if extra:
        raise HTTPException(422, f"unknown query parameter(s) {sorted(extra)}; for the cell type use 'ct' or its "
                                 f"alias 'cell_type'. Valid parameters: {sorted(allowed_params)}.")
    resolved = (cell_type or ct or "k562").lower()
    known = {c["id"] for c in _CELLTYPES}
    if resolved not in known:
        raise HTTPException(422, f"unknown cell type '{resolved}'; valid cell types: {sorted(known)} "
                                 f"(only k562/hepg2/hspc have a measured atlas; the others are a data-gated roadmap).")
    return resolved


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
def crosslink_writers(request: Request, chrom: str, bin: int, ct: str = "k562", cell_type: str | None = None):
    from pen_stack.atlas import crosslink as cl
    ct = _resolve_ct(request, ct, cell_type, {"chrom", "bin", "ct", "cell_type"})
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
def crosslink_loci(request: Request, family: str, ct: str = "k562", cell_type: str | None = None,
                   top: int = Query(20, le=200)):
    from pen_stack.atlas import crosslink as cl
    ct = _resolve_ct(request, ct, cell_type, {"family", "ct", "cell_type", "top"})
    try:
        loci = cl.loci_for_writer(family, ct, top=top)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    return {"family": family, "ct": ct, "loci": _records(loci), "disclaimer": _DISCLAIMER}


@app.get("/gene/location")
def gene_location(gene: str):
    """v7.1.5: the canonical chromosome of a gene (or safe-harbour locus nickname), for the UI's gene/chromosome
    concordance check. found=False when the gene is not in the coordinate table (no fabrication)."""
    from pen_stack.planner.chromosome import canonical_chromosome
    from pen_stack.planner.optimize import gene_region, resolve_gene
    try:
        reg = gene_region(gene)
    except Exception:  # noqa: BLE001 - coords table absent -> cannot resolve
        reg = None
    resolved = resolve_gene(gene)
    if reg is None:
        return {"gene": gene, "resolved": resolved, "found": False, "chrom": None}
    return {"gene": gene, "resolved": resolved, "found": True, "chrom": canonical_chromosome(reg[0]),
            "start": int(reg[1]), "end": int(reg[2])}


@app.get("/writable")
def writable(request: Request, gene: str, ct: str = "k562", cell_type: str | None = None,
             top: int = Query(20, le=200)):
    from pen_stack.atlas.crosslink import loci_for_gene
    ct = _resolve_ct(request, ct, cell_type, {"gene", "ct", "cell_type", "top"})
    try:
        g = loci_for_gene(gene, ct)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    cov = next((c["coverage"] for c in _CELLTYPES if c["id"] == ct), "unknown")
    # writability = 0.5*safety + 0.5*p_durable (an additive, decomposable mean -- NOT a product, and there is no
    # separate accessibility axis; chromatin enters as input features to the safety + durability models).
    meta = {"gene": gene, "ct": ct, "coverage": cov, "writability_formula": "0.5*safety + 0.5*p_durable",
            "coverage_note": ("partial chromatin panel for this cell type: durability degrades gracefully over the "
                              "missing tracks (still measured, not extrapolated)") if cov == "partial" else None,
            "disclaimer": _DISCLAIMER}
    if g.empty:
        return {**meta, "loci": []}
    cols = ["chrom", "bin", "safety", "p_durable", "writability"]
    return {**meta, "loci": _records(g[cols].head(top))}


# the cell types the Site Finder offers, with their HONEST coverage. A cell type returns writable loci only when
# its measured writability atlas (atlas_<ct>.parquet) is actually present; the rest are a data-gated roadmap,
# never a silently-failing dropdown option.
_CELLTYPES = [
    {"id": "k562", "label": "K562", "description": "chronic myelogenous leukemia line",
     "coverage": "full", "tracks": "ATAC + histones + TRIP durability + safety"},
    {"id": "hepg2", "label": "HepG2", "description": "hepatocellular carcinoma line",
     "coverage": "full", "tracks": "ATAC + histones + safety (partial TRIP)"},
    {"id": "hspc", "label": "HSPC", "description": "hematopoietic stem and progenitor cells",
     "coverage": "partial", "tracks": "ATAC + expression + genotoxicity; partial histone panel (graceful degradation)"},
    {"id": "h1_hesc", "label": "H1 hESC", "description": "H1 human embryonic stem cells", "coverage": "none", "tracks": ""},
    {"id": "ipsc", "label": "iPSC", "description": "induced pluripotent stem cells", "coverage": "none", "tracks": ""},
    {"id": "cd8_t", "label": "CD8 T", "description": "cytotoxic T lymphocytes", "coverage": "none", "tracks": ""},
    {"id": "pbmc", "label": "PBMC", "description": "peripheral blood mononuclear cells", "coverage": "none", "tracks": ""},
]


@app.get("/celltypes", tags=["site finder"])
def celltypes_endpoint():
    """Per cell type: whether a MEASURED writability atlas exists (so Site Finder returns real loci) and its
    coverage. Cell types without an atlas are a documented, data-gated roadmap, never a silently-failing option."""
    from pen_stack.atlas.crosslink import writability_path
    out = []
    for ct in _CELLTYPES:
        try:
            writability_path(ct["id"])
            measured = True
        except Exception: # noqa: BLE001
            measured = False
        cov = ct["coverage"] if measured else "none"
        out.append({**ct, "coverage": cov, "measured": measured,
                    "note": ct["tracks"] if measured else "no writability atlas built yet (data-gated roadmap)"})
    return {"cell_types": out, "measured_count": sum(c["measured"] for c in out),
            "disclaimer": "Only cell types with a measured writability atlas return loci; the rest are an honest, "
                          "data-gated roadmap, never a fabricated or silently-empty result."}


@app.get("/recommend", tags=["writer atlas"])
def recommend_endpoint(write_type: str = "insertion", cargo_bp: int = 2000, cell_type: str = "K562",
                       target_seq: str | None = None, donor_seq: str | None = None,
                       top_k: int = Query(8, le=30)):
    """Rank writer families for a write request (Stage C, C-WS5). KB readiness is the GROUNDED primary ranking;
    each family also carries a CANDIDATE learned efficiency with a trained split-conformal interval (C-WS2), and a
    dependency-free guide / att design (C-WS3) when target/donor sequences are supplied. No efficiency is ever
    fabricated for a family the curated dataset never saw (KB-only for those)."""
    from pen_stack.atlas.writer_recommend import recommend_writers
    req = {"write_type": write_type, "cargo_bp": cargo_bp, "cell_type": cell_type,
           "target_seq": (target_seq or "").strip() or None, "donor_seq": (donor_seq or "").strip() or None}
    return recommend_writers(req, top_k=top_k)


@app.get("/writer/efficiency", tags=["writer atlas"])
def writer_efficiency_endpoint():
    """The curated Writer-Efficiency dataset (C-WS1: real measured integration efficiencies, one row per condition
    with a DOI + verbatim quote) and the held-out Writer-Efficiency-Bench result (C-WS2 validation). Honest,
    pre-registered outcome: the learned predictor beats the KB family-mean baseline on held-out LOCUS (CI excludes
    0) but NOT on held-out FAMILY at this N, so the KB ranking is retained as primary and the predictor ships as a
    candidate advisory."""
    from pen_stack.atlas import writer_efficiency as we
    df = we.human_cell()
    cols = [c for c in ["system", "family", "variant", "cargo_bp", "locus", "cell_type",
                        "efficiency_pct", "specificity_pct", "doi", "quote"] if c in df.columns]
    bench = None
    p = _ATLAS.parents[2] / "benchmarks" / "writer_efficiency" / "result.json"
    if p.exists():
        bench = json.loads(p.read_text(encoding="utf-8"))
    return {"dataset_summary": we.provenance_summary(), "records": _records(df[cols]), "benchmark": bench,
            "note": "Measured, DOI-backed integration efficiencies (C-WS1). The bench is the contribution; the "
                    "learned predictor (C-WS2) is a candidate advisory, not the authoritative ranking."}


@app.get("/writer/variants", tags=["writer atlas"])
def writer_variants_endpoint(integrase: str | None = None, system: str | None = None):
    """Variant critique (C-WS4): retrospective recovery of known serine-integrase hyperactive mutants over a frozen
    DOI'd panel (NOT a blind sequence-only predictor), plus the honest deferral of the blind protein-LM recovery
    (no per-variant fitness endpoint exists, so it abstains rather than fabricate a positive). `system` is accepted
    as an alias for `integrase`; omit both to get the full panel."""
    from pen_stack.design import writer_variants as wv
    target = integrase or system  # accept either name; the panel is keyed by serine-integrase
    return {"hyperactive_recovery": wv.hyperactive_recovery(target),
            "blind_lm_recovery": wv.lm_recovery(),
            "panel": wv.hyperactive_panel(),
            "note": "Retrospective catalogue recovery is real and DOI-backed; the blind LM predictor is deferred "
                    "(reported as a known limitation, never a manufactured positive)."}


@app.get("/writer/immune", tags=["writer atlas"])
def writer_immune_endpoint():
    """The writer enzyme's immunogenicity as an antigen (v6.9 writer-as-antigen, surfaced in the Writer Atlas from
    v7.1.8): per genome-writer family, the real NetMHCIIpan-4.0 MHC-II/CD4 epitope load + the ADA-risk axis
    (MHC-II density x foreignness, self-tolerance filtered against the human proteome). Read from the committed
    cache - NOT recomputed. Population-level proxy, never a patient-specific magnitude (a known-unknown). The Cas9
    nuclease (an editor, not a large-cargo writer) and the human self control are excluded."""
    from pen_stack.planner.immune_profile import writer_immunogenicity_table
    return {"writers": writer_immunogenicity_table(),
            "method": "NetMHCIIpan-4.0 MHC-II epitope load + ADA risk (MHC-II density x foreignness, self-tolerance "
                      "filtered against the human proteome). Population-level proxy from the committed cache; the "
                      "realized CD4 response / ADA titer is a known-unknown.",
            "scale": "0-1, higher = lower risk (1 = least presentable / least ADA-driving)",
            "no_fabrication": True}


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
def plan(request: Request, gene: str, intent: str, cargo_bp: int = 2000, ct: str = "k562",
         cell_type: str | None = None, k: int = Query(5, le=20)):
    """Write Planner (Step 3.4): goal + edit_intent -> ranked, traceable plans."""
    from pen_stack.planner.optimize import EditIntent
    from pen_stack.planner.pipeline import plan_write
    ct = _resolve_ct(request, ct, cell_type, {"gene", "intent", "cargo_bp", "ct", "cell_type", "k"})
    try:
        intent_e = EditIntent(intent)
    except ValueError as e:
        raise HTTPException(422, f"unknown edit_intent: {intent}") from e
    try:
        plans = plan_write(gene, intent_e, cargo_bp, ct, k=k)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e)) from e
    cov = next((c["coverage"] for c in _CELLTYPES if c["id"] == ct), "unknown")
    return {"gene": gene, "intent": intent, "ct": ct, "coverage": cov, "n": len(plans), "plans": plans,
            "disclaimer": _DISCLAIMER}


@app.post("/verify")
def verify_endpoint(design: dict):
    """v3.3 verification service (WS-V): submit a proposed genomic write, get back a structured Verdict,
    legality + named rejections + calibrated confidence + epistemic status + scope flags. Legality and
    confidence are distinct axes. A `question` key (optional) is checked against the known-unknowns registry."""
    from pen_stack.verify import verify
    return verify(design).model_dump()


@app.post("/verify/proof")
def verify_proof_endpoint(design: dict):
    """v6.12 verification service (WS-VERIFY): the repair-oriented proof object. Returns the three axes
    (legality, confidence, biosecurity) reported separately, each with a status, the rule or signature that
    fired, evidence, and a repair hint; the collapsed verdict is None. An agent repairs a failed design from
    the legality axis's repair hint. A `question` key (optional) is checked against the known-unknowns."""
    from pen_stack.verify.proof import verify_proof
    return verify_proof(design).model_dump()


@app.post("/graph/query")
def graph_query_endpoint(q: dict):
    """v4.5 world-model graph (WS-G): multi-hop query. Body: {locus, cargo_form?}. Returns writers that
    reach the locus AND are deliverable by a cargo-form-compatible vehicle, each with its provenanced path."""
    from pen_stack.graph import writers_reaching_and_deliverable
    return writers_reaching_and_deliverable(q.get("locus"), cargo_form=q.get("cargo_form"))


# ======================================================================================
# v6.1, The AI Integration Surface: the self-describing contract + the engine tool routes.
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


@app.get("/oracles", tags=["v6.4 live oracles"])
def oracles_endpoint(probe: bool = False):
    """v6.4: per-foundation-model EXECUTION + LATENCY CLASS + live status (the 'tell the user the cost up front'
    surface). `?probe=true` pings the local GPU model servers. Live oracles answer in seconds, ~2 min; held cloud
    jobs (AF3/Boltz/Chai/Protenix) run separately and never block; deferred outcomes are never fabricated."""
    from pen_stack.oracles.status import oracle_status, summary
    return {"summary": summary(), "oracles": oracle_status(probe=bool(probe))}


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


@app.post("/offtarget", tags=["v6.10 off-target"])
def offtarget_endpoint(req: dict):
    """v6.10 PEN-OFFTGT cross-family off-target NOMINATION (NOT a clearance). Body:
    {writer_family, guide?, candidate_sites?, sequence?, accessibility?, assay?}. Returns ranked candidate
    off-targets with a real-data mismatch-calibrated risk band + the recommended validation assay; abstains
    without inputs and never fabricates sites."""
    from pen_stack.wgenome.offtarget_predict import nominate_offtargets
    return nominate_offtargets(
        req.get("writer_family", ""), guide=req.get("guide"), candidate_sites=req.get("candidate_sites"),
        sequence=req.get("sequence"), accessibility=req.get("accessibility"),
        target_core=req.get("target_core"), assay=req.get("assay", "guideseq"))


@app.get("/offtarget/assay", tags=["v6.10 off-target"])
def offtarget_assay_endpoint(writer_family: str):
    """v6.10 validation-assay recommendation for a writer family (the assay that would confirm a nomination)."""
    from pen_stack.wgenome.offtarget_assay import recommend_assay
    return recommend_assay(writer_family)


@app.get("/campaign", tags=["v7.0 closed-loop"])
def campaign_endpoint():
    """v7.0 Stage J: the validation-campaign engine. Returns the expression-validation campaign: the next batch of
    (cassette x locus x cell type) measurements ordered by expected information gain, the calibrate_axis gate it
    targets, and the active-vs-random result (reported verbatim). Cloud-lab-executable; Level 3, human in control;
    the experiments are candidates, the wet run is the standing bottleneck."""
    from pen_stack.active.campaign import design_campaign
    return design_campaign()


@app.post("/cloudlab", tags=["v7.0 closed-loop"])
def cloudlab_endpoint(req: dict):
    """v7.0 Stage J: safety-gated cloud-lab submission. Body: {design, experiment?, provider?, actor?}. The
    biosecurity gate runs BEFORE submission; a flagged design returns a structured refusal (blocked=True) and NO
    protocol is emitted. A cleared design returns a mock / dry-run job receipt (a real run needs a partner)."""
    from pen_stack.build.cloudlab import submit_gated
    return submit_gated(req.get("design", {}), req.get("experiment", {}),
                        provider=req.get("provider", "mock"), actor=str(req.get("actor", "api")))


@app.get("/brains", tags=["v7.0 closed-loop"])
def brains_endpoint():
    """v7.0 Stage J: benchmark the EIG/VOI experiment designer against the public SDL optimizers (BayBE / Atlas),
    reported verbatim with both cited (a win is not required; the result is falsifiable)."""
    from pen_stack.active.brains import benchmark
    return benchmark()


@app.post("/writespec", tags=["v6.14 writespec"])
def writespec_endpoint(req: dict):
    """v6.14 Stage A: parse a plain-language genome-writing request into a typed, ontology-backed WriteSpec.
    Body: {prose, overrides?, check_feasibility?}. Returns the typed spec (with per-field provenance), the
    assumptions behind every inferred field, clarifying questions for anything underspecified, the unresolved
    terms (kept null, never invented), the downstream design adapter, and the feasibility verdict. A WriteSpec is
    a REQUEST, not a claim; the extractor never fabricates intent."""
    from pen_stack.spec.service import parse_request
    return parse_request(req.get("prose", ""), overrides=req.get("overrides"),
                         check_feasibility=bool(req.get("check_feasibility", True)))


@app.post("/oracle/affinity", tags=["v6.13 oracle"])
def oracle_affinity_endpoint(req: dict):
    """v6.13 PEN-ORACLE protein-ligand binding-affinity (Boltz-2 head) under the oracle contract. Body:
    {protein_seq, ligand_smiles, pair_type?, ligand_name?}. Returns a CANDIDATE affinity (binder probability +
    predicted value) with native uncertainty, cache-or-abstain; protein-protein/protein-DNA pair types are
    flagged extrapolating (the head is protein-ligand only). Never runs the long job on the request path."""
    from pen_stack.oracles.affinity import predict_affinity
    r = predict_affinity(req.get("protein_seq", ""), req.get("ligand_smiles", ""),
                         pair_type=req.get("pair_type", "ligand"), ligand_name=req.get("ligand_name"))
    return r.model_dump()


@app.post("/delivery", tags=["v6.11 delivery"])
def delivery_endpoint(req: dict):
    """v6.11 PEN-DELIVER cross-modality delivery recommender. Body: {cargo_form, cargo_bp?, target_tissue?,
    safety_weight?, in_vivo?}. Returns ranked vehicles + a grounded serotype->tissue tropism prior (approved
    therapies; known-unknown for novel capsids) + the learned capsid-fitness bench. Never fabricates tropism."""
    from pen_stack.planner.delivery_predict import recommend_delivery_plus
    return recommend_delivery_plus(req.get("cargo_form", ""), req.get("cargo_bp"), req.get("target_tissue"),
                                   safety_weight=float(req.get("safety_weight", 0.5)), in_vivo=req.get("in_vivo"))


@app.post("/capsid_fitness", tags=["v6.11 delivery"])
def capsid_fitness_endpoint(req: dict):
    """v6.11 learned AAV capsid packaging-fitness for a VP1 sequence (FLIP-AAV-trained). Body: {vp1_sequence}.
    A CANDIDATE for the measured packaging axis, not an in-vivo tropism claim; abstains if the model is absent."""
    from pen_stack.planner.delivery_predict import capsid_fitness
    return capsid_fitness(req.get("vp1_sequence", ""))


@app.get("/delivery/tropism", tags=["v6.11 delivery"])
def delivery_tropism_endpoint(target_tissue: str):
    """v6.11 grounded AAV serotype->tissue tropism priors (approved therapies) for a target tissue, or a
    known-unknown when no approved serotype targets it."""
    from pen_stack.planner.delivery_predict import serotypes_for_tissue
    return serotypes_for_tissue(target_tissue)


@app.post("/generate", tags=["v6.1 AI surface"])
def generate_endpoint(req: dict):
    """v5.8 generative designer: verifier-as-discriminator. Body: {goal?, candidates?, keep?}. Hazardous/illegal
    candidates are discarded; survivors are calibrated + immune-profiled candidates (never asserted to work).

    v7.1.2: the GOAL'S cargo function is screened by the Guardian FIRST, before the vehicle x cargo sweep. A
    hazardous goal (e.g. a furin-cleavage tropism-enhancement or a dominant-negative tumor-suppressor ablation) is
    REFUSED up front and the response carries the explicit safety verdict, so an empty result is correctly
    attributed to a biosecurity refusal (not a silent 'no candidates'). The per-candidate Guardian still runs in
    verify() as defence in depth."""
    from pen_stack.design import generate_designs
    goal = req.get("goal")
    # Guardian pre-screen on the goal's declared cargo function (the artifact, not any free-text justification).
    if isinstance(goal, dict) and any(goal.get(f) for f in ("cargo_function", "cargo_seq")):
        from pen_stack.safety.gate import safety_gate
        screen = {f: goal[f] for f in ("cargo_function", "cargo_seq", "gene", "delivery_vehicle", "in_vivo",
                                       "delivery_tropism", "replication_competent") if goal.get(f) is not None}
        gv = safety_gate(screen, actor=str(req.get("actor", "api")))
        if gv.decision in ("refuse", "escalate"):
            return {"survivors": [], "refused": True,
                    "safety": {"decision": gv.decision, "reason": gv.reason,
                               "hits": [{"detail": h.detail, "severity": h.severity, "kind": h.kind}
                                        for h in gv.hits]},
                    "disclaimer": _DISCLAIMER}
    return {"survivors": generate_designs(goal, candidates=req.get("candidates"),
                                          keep=int(req.get("keep", 25)), actor=str(req.get("actor", "api"))),
            "refused": False, "disclaimer": _DISCLAIMER}


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
# v5.13, The Genome-Writing Challenge (read-only surface for the web Challenge page).
# Public tasks (NO labels) + the PEN-STACK reference submission that anchors the leaderboard. Submissions
# are Python `predict_fn`s scored offline (`benchmarks/genome_writing_challenge/run.py`), never accepted
# over HTTP, so these routes only EXPOSE the held-out round and the anchor score.
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
