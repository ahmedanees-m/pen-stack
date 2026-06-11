"""Grounded co-scientist for the web chat (PEN-STACK v6.2, WS-CHAT).

The conversational layer that is helpful **and** cannot fabricate. The flow is always:

    run_tools(message)  ->  the ENGINE computes every number (verify / safety / immune / scope)
    extract_grounded_numbers(tool_results)  ->  the allow-list of values the model may cite
    LLM narrates over the tool results  ->  Ollama (local, free) → Nemotron (hosted free tier) → deterministic
    _enforce_grounding(text, allow_list)  ->  HARD GATE: any number not traceable to a tool result is struck

The LLM *routes, explains, and compares*; it never sources a number. If both LLMs are unavailable the
deterministic narrator composes the reply directly from the tool results — so the science never depends on the
model. The grounding guard is the invariant: a numeric claim absent from the tool results cannot survive into a
reply (it is replaced with the marker ``[unverified]``). This is asserted by ``tests/unit/test_ws_chat.py``.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pen_stack.web.tools import extract_grounded_numbers, run_tools

SYSTEM = (
    "You are PEN-STACK's co-scientist for genome writing. You may explain, compare, and route between the "
    "engine's tools, but you MUST NOT state any number, score, probability, titer, or confidence that is not "
    "present verbatim in the TOOL RESULTS provided to you. If a value is not in the tool results, say it is "
    "out of scope or unknown — never invent it. Never invent a citation. Always surface uncertainty and the "
    "scope ledger ('what I can't tell you'). Be concise, friendly, and honest. This is decision-support, not a "
    "clinical directive."
)

# the number marker the guard substitutes for any ungrounded numeric token the model emits.
_UNVERIFIED = "[unverified]"
# a numeric token in model prose: optional sign, digits, optional decimal, optional %  (e.g. 0.28, 28%, 4500)
_TOKEN_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?")


# --------------------------------------------------------------------------------------
# the grounding guard (the hard gate)
# --------------------------------------------------------------------------------------
def _is_grounded(token: str, grounded: set[str]) -> bool:
    """A numeric token is grounded iff it (or a normalised form) appears in the engine's allow-list."""
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
    if pct:                                              # "28%" matches a grounded 0.28 score or a grounded 28
        forms.add(str(f / 100))
        forms.add(f"{f / 100:.2f}")
    return bool(forms & grounded)


def _enforce_grounding(text: str, grounded: set[str]) -> str:
    """Strike every numeric token in `text` that is not traceable to the engine's tool results. The result is
    a reply in which **no number is absent from the tool results** — the invariant the chat is built on."""
    return _TOKEN_RE.sub(lambda m: m.group(0) if _is_grounded(m.group(0), grounded) else _UNVERIFIED, text)


def ungrounded_numbers(text: str, grounded: set[str]) -> list[str]:
    """Diagnostic: the numeric tokens in `text` that are NOT in the allow-list (empty after enforcement)."""
    return [m.group(0) for m in _TOKEN_RE.finditer(text) if not _is_grounded(m.group(0), grounded)]


# --------------------------------------------------------------------------------------
# the deterministic narrator (no-LLM fallback; numbers grounded by construction)
# --------------------------------------------------------------------------------------
def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.2f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))
    return str(x)


def _deterministic_narrate(tr: dict) -> str:
    """Compose a clear English reply directly from the engine's tool results. Every number here comes straight
    from `tr`, so the reply is grounded by construction (this is the LLM-offline path)."""
    d = tr["parsed_design"]
    v = tr["verdict"]
    lines: list[str] = []
    lines.append(
        f"I read your goal as: a **{d['edit_intent'].replace('_', ' ')}** of **{d['gene']}** "
        f"(~{d['cargo_bp']} bp cargo) delivered by **{d['delivery_vehicle'].replace('_', ' ')}** "
        f"in **{d['cell_type']}**. Here is what the engine computes — every number below is tool-sourced.")

    legal = "legal" if v["legal"] else ("deferred" if v["legal"] is None else "ILLEGAL")
    line = f"**Verification.** The design is **{legal}** ({v['epistemic_status']})."
    if v["violations"]:
        line += " Violations: " + ", ".join(str(x) for x in v["violations"]) + "."
    if v["confidence"] is not None:
        band = f" [{v['interval'][0]:.2f}–{v['interval'][1]:.2f}]" if v.get("interval") else ""
        line += f" Calibrated confidence on the soft components: **{v['confidence']:.2f}**{band}."
    else:
        line += " (Confidence abstained — no calibrated soft-component score for this design.)"
    lines.append(line)

    s = tr["safety"]
    if s.get("decision"):
        lines.append(f"**Safety (Guardian).** Decision: **{s['decision']}** — {s.get('reason', 'n/a')}.")

    imm = tr["immune_profile"]
    axes = imm.get("axes") or {}
    if axes:
        lines.append("**Immune-risk profile** (per-axis — never collapsed into one number):")
        for name, a in axes.items():
            val = _fmt(a["value"]) if a.get("value") is not None else "n/a"
            unc = a.get("uncertainty")
            unc_s = f" ±{_fmt(unc)}" if unc is not None else ""
            lab = a.get("validation", "")
            lines.append(f"  • {name.replace('_', ' ')}: **{val}**{unc_s} — {lab}")
        if imm.get("collapsed_score") is None:
            lines.append("  (No single fused immune score is asserted — that would overstate certainty.)")

    sc = tr["scope"]
    if sc.get("out_of_scope"):
        lines.append(f"**Out of scope.** {sc.get('why') or sc.get('title')} PEN-STACK will not guess a value here.")
    ku = imm.get("known_unknowns") or []
    if ku:
        lines.append("**What I can't tell you** (known-unknowns): " + ", ".join(str(x) for x in ku) + ".")

    lines.append(f"_{tr['disclaimer']}_")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# LLM backends (free-tier first; both optional)
# --------------------------------------------------------------------------------------
def _ollama_base() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _llm_timeout() -> float:
    # generous by default: a 7B model narrating a full dossier on a single GPU can take ~60-90s; too short a
    # timeout would silently fall back to the deterministic narrator on every real query.
    return float(os.getenv("PEN_STACK_LLM_TIMEOUT", "150"))


def _call_ollama(prompt: str) -> str:
    """Primary: local Ollama (free). Default model qwen2.5:7b-instruct (override via OLLAMA_MODEL). Generation is
    bounded (num_predict) so a reply returns promptly; the science is in the engine, the LLM only narrates."""
    import requests

    r = requests.post(
        f"{_ollama_base()}/api/generate",
        json={"model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct"),
              "prompt": prompt, "system": SYSTEM, "stream": False,
              "options": {"temperature": 0.2,
                          "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "450"))}},
        timeout=_llm_timeout())
    r.raise_for_status()
    return r.json()["response"]


def _nvidia_key() -> str | None:
    key = os.getenv("NVIDIA_API_KEY")
    if key:
        return key.strip()
    f = Path(__file__).resolve().parents[2] / "configs" / "nvidia_api_key.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def _call_nemotron(prompt: str) -> str:
    """Fallback: NVIDIA-hosted Nemotron (free tier). Needs NVIDIA_API_KEY (or configs/nvidia_api_key.txt)."""
    import requests

    key = _nvidia_key()
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY")
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"),
              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
              "temperature": 0.2, "max_tokens": 900},
        timeout=_llm_timeout())
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _prompt(message: str, tool_results: dict, history: list | None) -> str:
    import json

    convo = ""
    for turn in (history or [])[-6:]:
        role = turn.get("role", "user")
        convo += f"{role.upper()}: {turn.get('content', '')}\n"
    return (f"{SYSTEM}\n\nTOOL RESULTS (the ONLY source of numbers — cite nothing else):\n"
            f"{json.dumps(tool_results, default=str, separators=(',', ':'))}\n\n{convo}USER: {message}\n\n"
            f"Compose a concise, friendly reply (a short paragraph) that explains the engine's findings, surfaces "
            f"the uncertainty and the scope ledger, and uses ONLY numbers present in the tool results.")


# --------------------------------------------------------------------------------------
# the public entry point
# --------------------------------------------------------------------------------------
def grounded_reply(message: str, history: list | None = None, *, allow_llm: bool = True) -> dict:
    """The grounded co-scientist. Runs the engine, then narrates over its results with the grounding guard
    enforced. Returns {reply, tool_results, grounded, backend}. `grounded` is always True: the reply is either
    composed deterministically from the tool results, or passed through `_enforce_grounding`."""
    tool_results = run_tools(message, history)                 # ENGINE computes every number
    grounded = extract_grounded_numbers(tool_results)          # the allow-list
    prompt = _prompt(message, tool_results, history)

    if allow_llm and os.getenv("PEN_STACK_NO_LLM") != "1":
        for backend in (_call_ollama, _call_nemotron):
            try:
                text = _enforce_grounding(backend(prompt), grounded)   # HARD GATE
                return {"reply": text, "tool_results": tool_results, "grounded": True,
                        "backend": backend.__name__.removeprefix("_call_")}
            except Exception:                                  # any backend failure → next, then deterministic
                continue

    return {"reply": _deterministic_narrate(tool_results), "tool_results": tool_results,
            "grounded": True, "backend": "deterministic"}
