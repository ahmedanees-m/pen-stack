"""The PEN-STACK agent (Phase 3, Step 3.9) - tool-use orchestration.

Given a natural-language goal ("durably express factor IX in hepatocytes"), the agent plans the whole
write by calling validated tools (writability -> reachable writers -> writer axes -> plan_write -> cited
literature) in a tool-calling loop driven by the configured LLM (hybrid: NVIDIA Nemotron with Ollama
fallback, via ``pen_stack.rag.llm.chat``). Guardrails: it obtains numbers ONLY from tool calls (no
free-text predictions), refuses clinical-directive prompts, and logs an auditable trace.

Graceful: if no LLM provider is reachable, ``run_agent`` returns a refusal-free deterministic fallback
that calls plan_write directly - so the platform degrades to the validated pipeline rather than failing.
"""
from __future__ import annotations

import json
from pathlib import Path

from pen_stack.agent.guardrails import DISCLAIMER, out_of_scope
from pen_stack.agent.tools import SCHEMAS, dispatch
from pen_stack.rag.llm import chat as llm_chat

_TRACES = Path(__file__).resolve().parents[2] / "out" / "agent_traces"

_SYSTEM = (
    "You are the PEN-STACK genome-writing planning agent. You MUST obtain every fact and number by "
    "calling the provided tools - never invent a number, gene, score, or citation. Plan a write by "
    "calling: writability, reachable_writers, writer_axes, plan_write, ask_literature. When you have "
    "enough tool results, write a short plan that cites which tool produced each number. Decision-support "
    "only - never give clinical directives.")


def _tool_response(style: str, call_id: str | None, content: str) -> dict:
    """Format a tool-result message for the provider's API style."""
    m = {"role": "tool", "content": content}
    if style == "openai" and call_id is not None:
        m["tool_call_id"] = call_id
    return m


def run_agent(goal: str, max_steps: int = 12, cfg: dict | None = None) -> dict:
    """Turn a goal into a cited, auditable plan. Numbers come only from tool calls."""
    refusal = out_of_scope(goal)
    if refusal:
        return {"refused": True, "plan": refusal, "trace": [], "disclaimer": DISCLAIMER}

    from pen_stack.rag.llm import load_llm_config
    step_timeout = int((cfg or load_llm_config()).get("agent_call_timeout", 60))
    msgs = [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": goal}]
    trace: list[dict] = []
    seen: set = set()

    for _ in range(max_steps):
        resp = llm_chat(msgs, tools=SCHEMAS, cfg=cfg, timeout=step_timeout)
        if resp is None:
            return _fallback(goal, trace)
        provider, style = resp.get("provider"), resp.get("style", "openai")
        calls = resp.get("tool_calls") or []
        if not calls:
            return {"refused": False, "plan": resp.get("content", "").strip(),
                    "trace": trace, "disclaimer": DISCLAIMER, "llm": True, "provider": provider}
        msgs.append(resp["raw"])                          # append the assistant turn verbatim
        raw_calls = resp["raw"].get("tool_calls") or []
        for i, c in enumerate(calls):
            name = c["function"]["name"]
            args = c["function"]["arguments"]
            call_id = (raw_calls[i].get("id") if i < len(raw_calls) else None)
            key = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
            if key in seen:
                msgs.append(_tool_response(style, call_id, json.dumps(
                    {"note": "already called with these args; use prior result and finalise the plan"})))
                continue
            seen.add(key)
            try:
                result = dispatch(name, args)            # VALIDATED tool only
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
            trace.append({"tool": name, "args": args, "result": result})
            msgs.append(_tool_response(style, call_id, json.dumps(result, default=str)))
    return {"refused": False, "plan": "(max steps reached)", "trace": trace,
            "disclaimer": DISCLAIMER, "llm": True}


def _fallback(goal: str, trace: list[dict]) -> dict:
    """Deterministic fallback when no LLM is reachable: call plan_write on a best-effort parse."""
    from pen_stack.planner.optimize import EditIntent
    gene = next((w for w in goal.replace(",", " ").split() if w.isupper() and len(w) >= 2), None)
    intent = EditIntent.SAFE_HARBOUR.value
    for kw, it in [("disrupt", "knock_in_with_disruption"), ("knock", "knock_in_with_disruption"),
                   ("durab", "high_durability_insertion"), ("enhancer", "regulatory_excision"),
                   ("repeat", "repeat_excision")]:
        if kw in goal.lower():
            intent = it
            break
    if not gene:
        return {"refused": False, "plan": "No target gene detected; LLM unavailable.",
                "trace": trace, "disclaimer": DISCLAIMER, "llm": False}
    res = dispatch("plan_write", {"gene": gene, "intent": intent})
    trace.append({"tool": "plan_write", "args": {"gene": gene, "intent": intent}, "result": res})
    return {"refused": False, "plan": f"[deterministic fallback] plan for {gene} ({intent})",
            "trace": trace, "disclaimer": DISCLAIMER, "llm": False}


def save_trace(result: dict, name: str) -> Path:
    _TRACES.mkdir(parents=True, exist_ok=True)
    p = _TRACES / f"{name}.json"
    p.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return p
