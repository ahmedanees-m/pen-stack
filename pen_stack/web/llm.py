"""Hybrid grounded co-scientist (PEN-STACK v6.3).

PEN-STACK's ENGINE is the brain: for anything it can compute, the number comes from the engine and the grounding
guard strikes any value the model can't trace. On top of that the assistant has general + biological intelligence
for greetings and textbook questions, but those are answered in a SEPARATE, explicitly-labelled lane so a
general-knowledge fact can never be mistaken for a PEN-STACK result. Four lanes (see web.router.classify):

  * design / explain → run the engine, narrate over the dossier + the metric guide (the guard runs; numbers are
    the engine's, the guide explains what they MEAN, scale, direction, reference band).
  * meta → answer about PEN-STACK itself from the LIVE capability facts (the guard runs over the facts).
  * general → the LLM's trained knowledge, prefixed "general knowledge, not PEN-STACK-verified", with a
    pointer to the engine wherever PEN-STACK could compute a concrete answer. No number is attributed to PEN-STACK.

Conversation memory: the last turns are passed in `history`, so follow-ups ("what does that 0.55 mean?") resolve
against the prior dossier. (The frontend keeps history in-session until refresh.)
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pen_stack.web.guide import enrich_axes, guide_for, metric_guide, pen_stack_facts
from pen_stack.web.router import classify, pen_stack_angles
from pen_stack.web.tools import extract_grounded_numbers, run_tools

# -------------------------------------------------------------------------------------- system prompts
SYSTEM_GROUNDED = (
    "You are PEN-STACK's co-scientist for genome writing. The PEN-STACK ENGINE computed the TOOL RESULTS; you "
    "explain and route, but you MUST NOT state any number, score, probability, writer/enzyme name, or delivery "
    "vehicle that is not present in the TOOL RESULTS or the METRIC GUIDE provided. NEVER invent a recommendation, "
    "a markdown table of made-up values, or a 'hypothetical' result, if the engine did not compute something, "
    "say so plainly. For every key number, explain what it MEANS in plain words, its scale, whether higher is "
    "better, the reference band, how it was computed, so the user understands the value, not just sees it. "
    "Surface uncertainty and the scope ledger ('what I can't tell you'). Be concise and friendly. "
    "Decision-support, not a clinical directive."
)
SYSTEM_META = (
    "You are PEN-STACK's co-scientist explaining the SYSTEM ITSELF (coverage, methods, accuracy). Answer using "
    "ONLY the FACTS provided (counts, families, axes, how each is computed, the grounding posture). Do not invent "
    "capabilities, counts, or accuracy claims. Be concise and precise; cite the numbers from the FACTS."
)
SYSTEM_GENERAL = (
    "You are PEN-STACK's assistant answering a GENERAL biology / genome-engineering question from your own trained "
    "knowledge. Answer clearly and helpfully at a graduate level. This is NOT a PEN-STACK calculation, so do NOT "
    "present any number as a PEN-STACK result or imply it is engine-verified. If PEN-STACK could compute a concrete, "
    "grounded answer for the user's case, mention that briefly. Keep it focused."
)

_UNVERIFIED = "[unverified]"
_TOKEN_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?")
_GENERAL_LABEL = " *General knowledge (from my training, not a PEN-STACK calculation):*"


# -------------------------------------------------------------------------------------- the grounding guard
def _is_grounded(token: str, grounded: set[str]) -> bool:
    raw = token.strip()
    pct = raw.endswith("%")
    body = raw[:-1] if pct else raw
    if body in grounded:
        return True
    try:
        f = float(body)
    except ValueError:
        return False
    forms = {body, str(int(f)) if f.is_integer() else str(f), f"{f:.2f}"}
    if pct:
        forms.add(str(f / 100))
        forms.add(f"{f / 100:.2f}")
    return bool(forms & grounded)


def _enforce_grounding(text: str, grounded: set[str]) -> str:
    return _TOKEN_RE.sub(lambda m: m.group(0) if _is_grounded(m.group(0), grounded) else _UNVERIFIED, text)


def ungrounded_numbers(text: str, grounded: set[str]) -> list[str]:
    return [m.group(0) for m in _TOKEN_RE.finditer(text) if not _is_grounded(m.group(0), grounded)]


# -------------------------------------------------------------------------------------- deterministic narrators
def _fmt(x):
    if isinstance(x, float):
        return f"{x:.2f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))
    return str(x)


def _narrate_plan(p: dict) -> str | None:
    """The actual writer/site recommendation as a self-explanatory line (or an explicit 'not found' note)."""
    if not p or not p.get("available"):
        return None
    if not p.get("found"):
        return f"**Recommended writer.** {p.get('why', 'no writable plan for this target.')}"
    bits = [f"the top writer family is **{p['recommended_writer']}**"]
    site = p.get("site") or {}
    if site.get("chrom"):
        bits.append(f"at **{site['chrom']}:bin{site.get('bin')}**")
    nums = []
    if p.get("safety") is not None:
        nums.append(f"safety {_fmt(p['safety'])}")
    if p.get("durability") is not None:
        nums.append(f"durability {_fmt(p['durability'])}")
    if p.get("score") is not None:
        nums.append(f"plan score {_fmt(p['score'])}")
    cap = p.get("cargo_capacity_bp")
    fit = p.get("cargo_fits_single_vector")
    cargo_note = ""
    if cap is not None:
        cargo_note = (f" Cargo capacity is **{cap} bp**; the assembled cassette "
                      f"({p.get('assembled_bp', '?')} bp) "
                      + ("fits a single vector" if fit else f"exceeds it → delivered as **{p.get('delivery', 'split/dual')}**")
                      + ".")
    alts = p.get("alternative_writers") or []
    alt_note = f" Alternatives: {', '.join(alts)}." if alts else ""
    return (f"**Recommended writer.** For this target {', '.join(bits)} "
            f"({'; '.join(nums)}).{cargo_note}{alt_note} (0-1 scores, higher = better.)")


def _deterministic_narrate(tr: dict) -> str:
    d = tr["parsed_design"]
    v = tr["verdict"]
    lines = [f"I read your goal as a **{d['edit_intent'].replace('_', ' ')}** of **{d['gene']}** "
             f"({d['chrom']}, ~{d['cargo_bp']} bp) by **{d['delivery_vehicle'].replace('_', ' ')}** "
             f"in **{d['cell_type']}**. Every number below is engine-computed."]
    plan_line = _narrate_plan(tr.get("plan") or {})
    if plan_line:
        lines.append(plan_line)
    legal = "legal" if v["legal"] else ("deferred" if v["legal"] is None else "ILLEGAL")
    line = f"**Verification.** The design is **{legal}** ({v['epistemic_status']})."
    if v["violations"]:
        line += " Violations: " + ", ".join(str(x) for x in v["violations"]) + "."
    g = guide_for("confidence")
    if v["confidence"] is not None:
        band = f" [{v['interval'][0]:.2f}, {v['interval'][1]:.2f}]" if v.get("interval") else ""
        line += f" Calibrated confidence: **{v['confidence']:.2f}**{band}, {g['means'].split('.')[0]}."
    else:
        line += " (Confidence abstained, no calibrated score for this design.)"
    lines.append(line)
    s = tr["safety"]
    if s.get("decision"):
        sd = (metric_guide().get("safety_decision") or {}).get(s["decision"], "")
        lines.append(f"**Safety (Guardian).** **{s['decision']}**, {s.get('reason', '')}. {sd}")
    axes = (tr["immune_profile"].get("axes") or {})
    if axes:
        lines.append("**Immune-risk profile** (per-axis, never collapsed; each is 0-1, higher = safer):")
        for name, a in axes.items():
            gd = guide_for(name) or {}
            val = _fmt(a["value"]) if a.get("value") is not None else "n/a"
            unc = f" ±{_fmt(a['uncertainty'])}" if a.get("uncertainty") is not None else ""
            # prefer the self-explanatory engine 'meaning' (says what the value means + the proxy caveat in words)
            meaning = a.get("meaning") or ((gd.get("means", "").split(".")[0]) if gd else "")
            lines.append(f" • **{gd.get('label', name)}: {val}{unc}**, {meaning}")
    ku = tr["immune_profile"].get("known_unknowns") or []
    if ku:
        lines.append("**What I can't tell you** (measured, never predicted): " + ", ".join(str(x) for x in ku) + ".")
    lines.append(f"_{tr['disclaimer']}_")
    return "\n".join(lines)


def _deterministic_meta(facts: dict) -> str:
    w = facts.get("writers", {})
    dv = facts.get("delivery", {})
    im = facts.get("immunogenicity", {})
    ac = facts.get("accuracy", {})
    lines = ["**What PEN-STACK covers (from the live engine):**"]
    if w.get("systems"):
        lines.append(f" • **Writers/enzymes:** {w['systems']} systems across {w['n_families']} families "
                     f"({', '.join(w.get('families', []))}).")
    if dv.get("n_vehicles"):
        lines.append(f" • **Delivery vehicles:** {dv['n_vehicles']} ({', '.join(dv.get('vehicles', []))}).")
    if im.get("n_axes"):
        lines.append(f" • **Immune-risk axes:** {im['n_axes']} ({', '.join(im.get('axes', []))}), never collapsed.")
    lines.append(f" • **Accuracy posture:** {ac.get('posture', '')}")
    lines.append(f" • **Not predicted:** {ac.get('what_is_NOT_predicted', '')}")
    return "\n".join(lines)


_ALIASES = {"nab": "preexisting_nab", "antibod": "preexisting_nab", "seroprev": "preexisting_nab",
            "peg": "anti_peg", "genotox": "genotoxicity", "oncogen": "genotoxicity", "epitope": "cd8_epitope",
            "cd8": "cd8_epitope", "t-cell": "cd8_epitope", "t cell": "cd8_epitope", "innate": "innate",
            "cpg": "innate", "confidence": "confidence", "interval": "confidence", "expression": "relative_expression",
            "durab": "relative_expression"}


def _explain_guides(message: str) -> dict:
    """Which metric cards a follow-up is asking about (by metric name or a common alias); all of them if unsure."""
    low = message.lower()
    metrics = metric_guide().get("metrics", {})
    named = [k for k in metrics if k.replace("_", " ") in low or k in low]
    named += [k for w, k in _ALIASES.items() if w in low and k not in named]
    return {k: guide_for(k) for k in (named or list(metrics)) if guide_for(k)}


def _deterministic_explain(guides: dict) -> str:
    lines = ["**How to read these PEN-STACK metrics** (the values themselves come from the engine):"]
    for k, g in guides.items():
        if not g:
            continue
        lines.append(f" • **{g.get('label', k)}**, {g.get('scale', '')}, {g.get('direction', '')}. "
                     f"{g.get('means', '')} _Computed: {g.get('computed', '')}_ "
                     f"Bands: {g.get('bands', '')}. {g.get('reference', '')}")
    lines.append(f"_{(metric_guide() or {}).get('disclaimer', '')}_")
    return "\n".join(lines)


def _angles_footer(message: str) -> str:
    angles = pen_stack_angles(message)
    if not angles:
        return ""
    tips = " \n".join(f"• **{a['module']}**, try: _\"{a['example']}\"_" for a in angles)
    return ("\n\n---\n **PEN-STACK can compute a grounded answer for your case** (not just general knowledge): \n"
            + tips)


# -------------------------------------------------------------------------------------- LLM backends
def _ollama_base():
    return os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _llm_timeout():
    return float(os.getenv("PEN_STACK_LLM_TIMEOUT", "150"))


def _call_ollama(prompt, system):
    import requests
    r = requests.post(f"{_ollama_base()}/api/generate",
                      json={"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct"), "prompt": prompt,
                            "system": system, "stream": False, "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "30m"),
                            "options": {"temperature": 0.2, "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "450"))}},
                      timeout=_llm_timeout())
    r.raise_for_status()
    return r.json()["response"]


def _nvidia_key():
    key = os.getenv("NVIDIA_API_KEY")
    if key:
        return key.strip()
    f = Path(__file__).resolve().parents[2] / "configs" / "nvidia_api_key.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def _call_nemotron(prompt, system):
    import requests
    key = _nvidia_key()
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY")
    r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1"),
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                            "temperature": 0.2, "max_tokens": 700}, timeout=_llm_timeout())
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _run_llm(prompt, system):
    """Try the configured backends in order; return (text, backend) or (None, None)."""
    if os.getenv("PEN_STACK_NO_LLM") == "1":
        return None, None
    backends = {"ollama": _call_ollama, "nemotron": _call_nemotron}
    for name in [b.strip().lower() for b in os.getenv("PEN_STACK_LLM_ORDER", "ollama,nemotron").split(",")]:
        fn = backends.get(name)
        if fn is None:
            continue
        try:
            return fn(prompt, system), name
        except Exception:
            continue
    return None, None


def _history_block(history):
    out = ""
    for turn in (history or [])[-8:]:
        role = turn.get("role", "user")
        out += f"{role.upper()}: {turn.get('content', '')}\n"
    return out


# -------------------------------------------------------------------------------------- pre-route safety screen
# Defence-in-depth: a hazard-adjacent message gets the Guardian (biosecurity gate) BEFORE lane routing, so a
# hazardous request that would route to general/explain/meta (no design signal) is still screened, not only the
# design lane. The Guardian is framing-stripped and is the AUTHORITY on the decision; this broad regex only
# decides WHETHER to invoke it (benign chat skips it, and a false-positive trigger is harmless, the Guardian
# clears generic biology). Aligned with configs/safety/hazard_registry.yaml.
_HAZARD_RE = re.compile(
    r"\b(toxin|ricin|abrin|botulin(?:um)?|bont|anthrax|protective[- ]antigen|lethal[- ]factor|edema[- ]factor|"
    r"shiga|verotoxin|conotoxin|saxitoxin|tetrodotoxin|tetanus|diphtheria|cholera|enterotoxin|superantigen|"
    r"ribosome[- ]?inactivating|clostridial|nerve[- ]agent|sarin|soman|tabun|vx|novichok|smallpox|variola|"
    r"ebola|marburg|nipah|hendra|lassa|h[ae]?morrhagic[- ]fever|select[- ]agent|bioweapon|biological[- ]weapon|"
    r"biothreat|gain[- ]of[- ]function|pathogen|virulence)\b", re.I)


def _pre_route_safety(message: str):
    """If the message is hazard-adjacent, run the Guardian (framing-stripped) on it BEFORE lane routing. Returns a
    SafetyVerdict when the decision is refuse/escalate (the caller short-circuits to a decline), else None."""
    if not _HAZARD_RE.search(message or ""):
        return None
    try:
        from pen_stack.safety import safety_gate
        verdict = safety_gate({"cargo_function": (message or "").strip()}, actor="chat")
    except Exception: # noqa: BLE001 - the screen must never crash the chat; design lane still screens via run_tools
        return None
    return verdict if getattr(verdict, "decision", None) in {"refuse", "escalate"} else None


def _safety_decline(verdict) -> dict:
    reason = (getattr(verdict, "reason", None) or "matched a biosecurity hazard signature").strip()
    reply = (
        f" **Declined by the biosecurity screen (Guardian).** This request was assessed as **{verdict.decision}** "
        f", {reason}\n\nPEN-STACK is a genome-writing co-scientist with a dual-use safety gate; it does not help "
        "design, express, or enhance select-agent toxins or pathogens. If this was a general scientific question, "
        "please rephrase it without a build/express intent.")
    return {"mode": "safety", "provenance": "pen-stack", "grounded": True, "reply": reply, "backend": "guardian",
            "tool_results": {"safety": {"decision": verdict.decision, "reason": verdict.reason}},
            "angles": None, "facts": None}


# -------------------------------------------------------------------------------------- the public entry point
def grounded_reply(message: str, history: list | None = None, *, allow_llm: bool = True) -> dict:
    """Route the message to a lane and answer it. Returns {reply, mode, provenance, grounded, backend,
    tool_results?, facts?, angles?}. The first three lanes are engine-grounded (guard ON); the 'general' lane is
    explicitly labelled trained-knowledge and never attributes a number to PEN-STACK."""
    # Defence-in-depth: screen hazard-adjacent messages with the Guardian BEFORE routing, so a hazardous request
    # that would land in general/explain/meta (no design signal) is still refused, not only the design lane.
    verdict = _pre_route_safety(message)
    if verdict is not None:
        return _safety_decline(verdict)

    mode = classify(message, history)
    hist = _history_block(history)

    # ---- GENERAL: grounded by retrieval (PEN-RAG, v7.1) - retrieve -> cite-or-silence -> guard, else ABSTAIN.
    # The General lane no longer answers from the model's unsourced trained knowledge: every general answer is
    # backed by the provenance-tagged corpus (labelled 'literature-cited'), or the system abstains. ----
    if mode == "general":
        angles = pen_stack_angles(message)
        try:
            from pen_stack.rag.ground import ground_general
            g = ground_general(message, allow_llm=allow_llm)
        except Exception:  # noqa: BLE001 - corpus/retriever unavailable -> abstain, never fall back to ungrounded priors
            g = None
        if g is not None:
            base = {"mode": "general", "provenance": g["provenance"], "grounded": g["grounded"], "angles": angles,
                    "tool_results": None, "sources": g.get("sources"), "retrieval": g.get("retrieval"),
                    "status": g.get("status")}
            return {**base, "reply": g["reply"] + _angles_footer(message), "backend": g["backend"]}
        base = {"mode": "general", "provenance": "abstained", "grounded": False, "angles": angles,
                "tool_results": None, "sources": []}
        return {**base, "reply": ("The grounded literature corpus is unavailable right now, so I won't answer from "
                "unsourced general knowledge. PEN-STACK's engine can still compute grounded answers."
                + _angles_footer(message)), "backend": "deterministic"}

    # ---- META: facts about PEN-STACK itself (grounded over the live facts) ----
    if mode == "meta":
        facts = pen_stack_facts()
        allow = extract_grounded_numbers(facts)
        base = {"mode": "meta", "provenance": "pen-stack", "grounded": True, "facts": facts, "tool_results": None}
        if allow_llm:
            prompt = (f"FACTS (the only source of numbers):\n{json.dumps(facts, default=str)}\n\n{hist}"
                      f"USER: {message}\n\nAnswer about PEN-STACK using only the FACTS.")
            text, backend = _run_llm(prompt, SYSTEM_META)
            if text:
                return {**base, "reply": _enforce_grounding(text, allow), "backend": backend}
        return {**base, "reply": _deterministic_meta(facts), "backend": "deterministic"}

    # ---- EXPLAIN: interpret a value already on the table (the prior dossier lives in `history`) ----
    if mode == "explain":
        guides = _explain_guides(message)
        # grounded = the numbers already in the conversation (engine-computed earlier) + the metric-guide numbers
        allow = extract_grounded_numbers({"prior": hist, "guides": guides})
        base = {"mode": "explain", "provenance": "pen-stack", "grounded": True, "tool_results": None,
                "angles": None, "facts": None}
        if allow_llm:
            prompt = (f"METRIC GUIDE (how to read PEN-STACK's numbers):\n{json.dumps(guides, default=str)}\n\n"
                      f"CONVERSATION SO FAR (the numbers here were computed by the engine earlier):\n{hist}\n"
                      f"USER: {message}\n\nExplain what the value(s) mean using the metric guide, the scale, "
                      f"whether higher is better, the reference band, and how it was computed. Use ONLY numbers "
                      f"already in the conversation or the metric guide; do not introduce new ones.")
            text, backend = _run_llm(prompt, SYSTEM_GROUNDED)
            if text:
                return {**base, "reply": _enforce_grounding(text, allow), "backend": backend}
        return {**base, "reply": _deterministic_explain(guides), "backend": "deterministic"}

    # ---- DESIGN: run the engine, narrate + interpret over the dossier (guard ON) ----
    tr = run_tools(message, history)
    tr["immune_profile"]["axes"] = enrich_axes(tr["immune_profile"].get("axes") or {})
    guides = {k: guide_for(k) for k in (list((tr["immune_profile"].get("axes") or {}).keys())
                                        + ["confidence", "relative_expression"]) if guide_for(k)}
    bands = metric_guide().get("safety_decision", {})
    allow = extract_grounded_numbers(tr) | extract_grounded_numbers({"guides": guides})
    base = {"mode": mode, "provenance": "pen-stack", "grounded": True, "tool_results": tr,
            "angles": None, "facts": None}
    if allow_llm:
        prompt = (f"TOOL RESULTS (the only source of THIS design's numbers, including the recommended writer in "
                  f"`plan`):\n{json.dumps(tr, default=str)}\n\n"
                  f"METRIC GUIDE (use to EXPLAIN what each number means, scale, direction, reference band; you "
                  f"may cite band thresholds):\n{json.dumps(guides, default=str)}\n"
                  f"SAFETY DECISIONS:\n{json.dumps(bands)}\n\n{hist}USER: {message}\n\n"
                  f"Reply with: (1) the engine's findings WITH the numbers, if the user asked which writer, lead "
                  f"with `plan.recommended_writer` and its site/scores (do NOT name any other writer or vehicle), "
                  f"(2) what each key number MEANS in plain words (scale, what's good/bad, reference range), "
                  f"(3) the uncertainty + scope ledger. STRICT: use ONLY numbers present in the tool results or the "
                  f"metric guide; do NOT invent a writer name, a vehicle, a table, or any number. If something "
                  f"isn't in the tool results, say it is not computed.")
        text, backend = _run_llm(prompt, SYSTEM_GROUNDED)
        if text:
            cleaned = _enforce_grounding(text, allow)
            # Defence against fabrication-spam: if the model invented a lot of numbers (the guard struck many),
            # the narrated reply is unreadable ([unverified] everywhere), fall back to the deterministic,
            # fully-grounded narration so the user always gets a clean, traceable answer.
            if cleaned.count(_UNVERIFIED) >= 2:
                return {**base, "reply": _deterministic_narrate(tr), "backend": f"deterministic (guard:{backend})"}
            return {**base, "reply": cleaned, "backend": backend}
    return {**base, "reply": _deterministic_narrate(tr), "backend": "deterministic"}
