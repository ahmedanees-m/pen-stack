"""Engine tool-runner for the grounded co-scientist (PEN-STACK v6.2, WS-CHAT support).

The chat NEVER sources a number. This module is where the ENGINE computes everything: it parses a plain-language
goal, runs the validated tools (verify -> legality + safety + calibrated confidence + immune profile; the scope
matcher for known-unknowns), and returns a structured "dossier" of grounded facts. `extract_grounded_numbers`
returns the allow-list of values the LLM is permitted to cite, anything else it emits is stripped by the
grounding guard. No LLM is involved here; this is deterministic.
"""
from __future__ import annotations

import re
from typing import Any

# tiny, transparent keyword maps (the engine grounds everything; this only routes a plain-language goal).
_VEHICLES = {"aav": "AAV_single", "aav single": "AAV_single", "aav dual": "AAV_dual", "dual aav": "AAV_dual",
             "lentivir": "lentivirus", "lnp": "lnp_mrna", "mrna": "lnp_mrna", "adenovir": "helper_dependent_adenovirus",
             "hsv": "hsv_amplicon", "electroporat": "electroporation"}
_INTENTS = {"safe harbour": "safe_harbour_insertion", "safe harbor": "safe_harbour_insertion",
            "knock-in": "knock_in_with_disruption", "knock in": "knock_in_with_disruption",
            "knockin": "knock_in_with_disruption", "durab": "high_durability_insertion",
            "excis": "regulatory_element_excision", "regulator": "regulatory_element_excision",
            "landing pad": "landing_pad_insertion", "repeat": "repeat_excision"}
_CELLS = {"liver": "hepg2", "hepato": "hepg2", "hepg2": "hepg2", "hspc": "hspc", "stem cell": "h1_hesc",
          "ipsc": "ipsc", "k562": "k562", "t cell": "cd8_t", "t-cell": "cd8_t", "car-t": "cd8_t", "pbmc": "pbmc"}
_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b") # crude gene-symbol token (AAVS1, TRAC, FIX, ...)
_KB_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kb", re.I)
_BP_RE = re.compile(r"(\d{3,6})\s*bp", re.I)
# uppercase tokens that look like a gene but are not one (jargon / vehicle / form abbreviations)
_GENE_STOP = {"DNA", "RNA", "MRNA", "AAV", "LNP", "HSV", "CAR", "RNP", "PCR", "WT", "KO", "KI", "ITR",
              "ORF", "UTR", "CDS", "GFP", "ID", "QC", "VG", "MOI", "HLA", "MHC", "CRISPR", "CAS", "TF"}
# safe-harbour locus nicknames whose text collides with a vehicle keyword (AAVS1 ⊃ "aav"), stripped before
# vehicle matching so the user's stated vehicle (e.g. lentivirus) is not overridden by the locus name.
_SAFE_HARBOUR_RE = re.compile(r"\b(aavs1|h11|hipp11|rosa26)\b", re.I)


def _first(text: str, table: dict, default):
    low = text.lower()
    for key, val in table.items():
        if key in low:
            return val
    return default


def _resolve_chrom(gene: str) -> str | None:
    """The real chromosome for a gene symbol (or a safe-harbour nickname like AAVS1); None if not resolvable
    offline. So a chat goal about ITGB2 carries chr21, not a hardcoded default. Atlas-gated, never fabricates."""
    try:
        from pen_stack.planner.optimize import gene_region, resolve_gene
        reg = gene_region(resolve_gene(gene))
        return reg[0] if reg else None
    except Exception: # noqa: BLE001 - data/atlas absent (CI/offline) -> caller falls back to the default
        return None


def parse_goal(message: str) -> dict:
    """Best-effort parse of a plain-language goal into a Design/Goal dict. The engine grounds everything; this
    just picks a starting point (with sensible defaults) so the tools can run."""
    cargo = 3000
    if (m := _KB_RE.search(message)):
        cargo = int(float(m.group(1)) * 1000)
    elif (m := _BP_RE.search(message)):
        cargo = int(m.group(1))
    genes = [g for g in _GENE_RE.findall(message) if g not in _GENE_STOP]
    gene = genes[0] if genes else "AAVS1"
    # Vehicle matching is substring-based (so "lentivir" catches "lentiviral"); but the safe-harbour nickname
    # "AAVS1" contains "aav", which would wrongly match the AAV vehicle even when the user said lentivirus/LNP.
    # Strip those nicknames from the vehicle-search text first so the stated vehicle wins.
    veh_text = _SAFE_HARBOUR_RE.sub(" ", message.lower())
    return {"write_type": "insertion", "gene": gene, "chrom": _resolve_chrom(gene) or "chr19",
            "edit_intent": _first(message, _INTENTS, "safe_harbour_insertion"),
            "delivery_vehicle": _first(veh_text, _VEHICLES, "AAV_single"), "cargo_bp": cargo,
            "cell_type": _first(message, _CELLS, "k562"),
            # the user's plain-language goal IS the cargo-function description the Guardian must screen, so a
            # message like "express a ricin toxin" is biosecurity-screened, not silently passed as benign.
            "cargo_function": message.strip()}


# the chat's free-text intents map onto the planner's EditIntent enum (landing-pad/regulatory have nearest valid).
_INTENT_TO_ENUM = {"safe_harbour_insertion": "safe_harbour_insertion",
                   "high_durability_insertion": "high_durability_insertion",
                   "knock_in_with_disruption": "knock_in_with_disruption",
                   "regulatory_element_excision": "regulatory_excision",
                   "repeat_excision": "repeat_excision",
                   "landing_pad_insertion": "safe_harbour_insertion"}

# plain-language reading of each immune axis (0-1, higher = safer), so a value is self-explanatory in the reply.
_AXIS_DIRECTION = {
    "genotoxicity": "higher = safer (less integration-site oncogene risk; 1.0 = episomal / non-integrating)",
    "cd8_epitope": "higher = fewer strong CD8/MHC-I capsid epitopes (1.0 = non-viral / none)",
    "innate": "higher = less innate (CpG/TLR9, RIG-I) sensing of the delivered cargo",
    "preexisting_nab": "higher = fewer patients excluded by pre-existing neutralizing antibodies to the vector",
    "anti_peg": "higher = lower pre-existing anti-PEG barrier to re-dosing (PEGylated vehicles only)",
}


def _band_word(v: float) -> str:
    return "favourable" if v >= 0.7 else ("moderate" if v >= 0.4 else "a concern")


def axis_meaning(name: str, value, validation: str | None) -> str:
    """A self-explanatory, plain-language reading of one immune axis: what the number means + the proxy caveat."""
    if value is None:
        return "out of scope for this design, not predicted (no applicable mechanism)."
    direction = _AXIS_DIRECTION.get(name, "0-1, higher = safer")
    s = f"{float(value):.2f} on a 0-1 scale, {_band_word(float(value))}; {direction}."
    if validation and ("proxy" in validation.lower() or "not outcome-validated" in validation.lower()):
        s += (" This is a mechanistically/population-computed PROXY, it is not validated against a measured "
              "clinical outcome, so read it as a directional estimate, not a guaranteed result.")
    return s


def _run_planner(design: dict) -> dict[str, Any]:
    """The ACTUAL writer/site recommendation for the goal (atlas-gated). This is what makes a 'which writer can
    integrate N kb in GENE' question real: a named writer family, the top site, cargo-capacity fit, delivery,
    all engine-computed. Computed when the gene isn't in the atlas or the atlas isn't mounted; NEVER fabricates."""
    try:
        from pen_stack.planner.optimize import EditIntent
        from pen_stack.planner.pipeline import plan_write
    except Exception: # noqa: BLE001
        return {"available": False, "why": "planner unavailable in this environment"}
    intent = _INTENT_TO_ENUM.get(design.get("edit_intent"), "safe_harbour_insertion")
    try:
        plans = plan_write(design["gene"], EditIntent(intent), int(design["cargo_bp"]),
                           design.get("cell_type", "k562"), k=3)
    except FileNotFoundError:
        return {"available": False, "why": "writability atlas not mounted (planner runs on the live app only)"}
    except Exception as e: # noqa: BLE001 - never let a planner error break the chat dossier
        return {"available": False, "why": f"planner error: {type(e).__name__}"}
    if not plans:
        return {"available": True, "found": False, "gene": design["gene"],
                "why": (f"no writable plan for '{design['gene']}', it is not in the writability atlas. Check it "
                        "is an HGNC gene symbol or a known safe-harbour nickname (AAVS1, H11/HIPP11).")}
    top = plans[0]
    cargo = top.get("cargo") or {}
    return {"available": True, "found": True, "n_plans": len(plans),
            "recommended_writer": top.get("writer"), "site": top.get("site"),
            "safety": top.get("safety"), "durability": top.get("durability"), "score": top.get("score"),
            "writer_activity": top.get("writer_activity"), "reachability_tier": top.get("reachability_tier"),
            "cargo_capacity_bp": cargo.get("cargo_capacity_bp"), "assembled_bp": cargo.get("assembled_bp"),
            "cargo_fits_single_vector": cargo.get("size_ok"),
            "delivery": (top.get("delivery") or {}).get("delivery"),
            # distinct OTHER writer families (the top-k can repeat one family across sites, don't list it twice)
            "alternative_writers": sorted({p.get("writer") for p in plans[1:]
                                           if p.get("writer") and p.get("writer") != top.get("writer")})}


def run_tools(message: str, history: list | None = None) -> dict[str, Any]:
    """Run the validated engine over a plain-language message and return a grounded dossier. EVERY number here
    is computed by the engine (verify / planner / scope), no fabrication, no LLM."""
    from pen_stack.agent.scope import match_scope
    from pen_stack.verify import verify

    design = parse_goal(message)
    v = verify(dict(design), question=message)
    imm = v.immune_profile or {}
    axes = {k: {"value": a.get("value"), "uncertainty": a.get("uncertainty"),
                "validation": a.get("validation"), "in_scope": a.get("in_scope"),
                "meaning": axis_meaning(k, a.get("value"), a.get("validation"))}
            for k, a in (imm.get("axes") or {}).items()}
    oos = match_scope(message) # is the QUESTION out of scope (a known-unknown)?
    return {
        "parsed_design": design,
        "plan": _run_planner(design), # the actual writer/site recommendation (atlas-gated)
        "verdict": {"legal": v.legal, "confidence": v.confidence, "interval": v.interval,
                    "epistemic_status": v.epistemic_status,
                    "violations": [x.get("rule_id") for x in v.violations]},
        "safety": {"decision": (v.safety.decision if v.safety else None),
                   "reason": (v.safety.reason if v.safety else None)},
        "immune_profile": {"axes": axes, "collapsed_score": imm.get("collapsed_score"),
                           "known_unknowns": imm.get("known_unknowns")},
        "scope": ({"out_of_scope": True, "id": oos["id"], "title": oos["title"], "why": oos.get("deferral")}
                  if oos else {"out_of_scope": False}),
        "disclaimer": "Decision-support only; not a clinical directive. Every number is tool-sourced.",
    }


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_grounded_numbers(tool_results: dict) -> set[str]:
    """The allow-list: every numeric string that appears in the engine's tool results. The grounding guard
    permits the LLM to cite ONLY these; any other number it emits is stripped."""
    import json
    text = json.dumps(tool_results, default=str)
    grounded = set(_NUM_RE.findall(text))
    # also allow the common normalised forms (e.g. 0.5 / .5 / 50%) of each grounded value
    extra = set()
    for n in list(grounded):
        try:
            f = float(n)
        except ValueError:
            continue
        extra.add(str(int(f)) if f.is_integer() else str(f))
        extra.add(f"{f:.2f}")
        if 0 <= f <= 1:
            extra.add(str(round(f * 100))) # percent form of a [0,1] score
    return grounded | extra
