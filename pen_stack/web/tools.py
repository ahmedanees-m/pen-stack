"""Engine tool-runner for the grounded co-scientist (PEN-STACK v6.2, WS-CHAT support).

The chat NEVER sources a number. This module is where the ENGINE computes everything: it parses a plain-language
goal, runs the validated tools (verify -> legality + safety + calibrated confidence + immune profile; the scope
matcher for known-unknowns), and returns a structured "dossier" of grounded facts. `extract_grounded_numbers`
returns the allow-list of values the LLM is permitted to cite — anything else it emits is stripped by the
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
_GENE_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,7})\b")             # crude gene-symbol token (AAVS1, TRAC, FIX, ...)
_KB_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kb", re.I)
_BP_RE = re.compile(r"(\d{3,6})\s*bp", re.I)


def _first(text: str, table: dict, default):
    low = text.lower()
    for key, val in table.items():
        if key in low:
            return val
    return default


def parse_goal(message: str) -> dict:
    """Best-effort parse of a plain-language goal into a Design/Goal dict. The engine grounds everything; this
    just picks a starting point (with sensible defaults) so the tools can run."""
    cargo = 3000
    if (m := _KB_RE.search(message)):
        cargo = int(float(m.group(1)) * 1000)
    elif (m := _BP_RE.search(message)):
        cargo = int(m.group(1))
    genes = [g for g in _GENE_RE.findall(message) if g not in {"DNA", "RNA", "AAV", "LNP", "HSV", "CAR"}]
    gene = genes[0] if genes else "AAVS1"
    return {"write_type": "insertion", "gene": gene, "chrom": "chr19",
            "edit_intent": _first(message, _INTENTS, "safe_harbour_insertion"),
            "delivery_vehicle": _first(message, _VEHICLES, "AAV_single"), "cargo_bp": cargo,
            "cell_type": _first(message, _CELLS, "k562"),
            # the user's plain-language goal IS the cargo-function description the Guardian must screen — so a
            # message like "express a ricin toxin" is biosecurity-screened, not silently passed as benign.
            "cargo_function": message.strip()}


def run_tools(message: str, history: list | None = None) -> dict[str, Any]:
    """Run the validated engine over a plain-language message and return a grounded dossier. EVERY number here
    is computed by the engine (verify / scope) — no fabrication, no LLM."""
    from pen_stack.agent.scope import match_scope
    from pen_stack.verify import verify

    design = parse_goal(message)
    v = verify(dict(design), question=message)
    imm = v.immune_profile or {}
    axes = {k: {"value": a.get("value"), "uncertainty": a.get("uncertainty"),
                "validation": a.get("validation"), "in_scope": a.get("in_scope")}
            for k, a in (imm.get("axes") or {}).items()}
    oos = match_scope(message)                                # is the QUESTION out of scope (a known-unknown)?
    return {
        "parsed_design": design,
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
            extra.add(str(round(f * 100)))                    # percent form of a [0,1] score
    return grounded | extra
