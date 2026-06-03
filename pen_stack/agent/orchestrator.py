"""The PEN-STACK agent (Phase 3, Step 3.9) - tool-use orchestration.

Given a natural-language goal ("durably express factor IX in hepatocytes"), the agent plans the whole
write by calling validated tools (writability -> reachable writers -> writer axes -> plan_write -> cited
literature) in a tool-calling loop driven by a local LLM (Ollama/Qwen2.5-7B). Guardrails: it obtains
numbers ONLY from tool calls (no free-text predictions), refuses clinical-directive prompts, and logs an
auditable trace (every tool call's inputs + outputs + source).

Graceful: if no LLM endpoint is reachable, ``run_agent`` returns a refusal-free deterministic fallback
that calls plan_write directly - so the platform degrades to the validated pipeline rather than failing.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml

from pen_stack.agent.guardrails import DISCLAIMER, out_of_scope
from pen_stack.agent.tools import SCHEMAS, dispatch

_LLM_CFG = Path(__file__).resolve().parents[2] / "configs" / "llm.yaml"
_TRACES = Path(__file__).resolve().parents[2] / "out" / "agent_traces"

_SYSTEM = (
    "You are the PEN-STACK genome-writing planning agent. You MUST obtain every fact and number by "
    "calling the provided tools - never invent a number, gene, score, or citation. Plan a write by "
    "calling: writability, reachable_writers, writer_axes, plan_write, ask_literature. When you have "
    "enough tool results, write a short plan that cites which tool produced each number. Decision-support "
    "only - never give clinical directives.")


def _llm_cfg() -> dict:
    return yaml.safe_load(_LLM_CFG.read_text(encoding="utf-8"))


def _ollama_chat(messages: list[dict], tools: list[dict], cfg: dict, timeout: int = 180) -> dict | None:
    base = cfg.get("api_base", "http://localhost:11434")
    model = str(cfg.get("model", "qwen2.5:7b-instruct")).split("/")[-1]
    payload = {"model": model, "messages": messages, "tools": tools, "stream": False,
               "options": {"temperature": float(cfg.get("temperature", 0.1))}}
    try:
        req = urllib.request.Request(f"{base}/api/chat", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:  # noqa: BLE001
        return None


def run_agent(goal: str, max_steps: int = 12, cfg: dict | None = None) -> dict:
    """Turn a goal into a cited, auditable plan. Numbers come only from tool calls."""
    refusal = out_of_scope(goal)
    if refusal:
        return {"refused": True, "plan": refusal, "trace": [], "disclaimer": DISCLAIMER}

    cfg = cfg or _llm_cfg()
    msgs = [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": goal}]
    trace: list[dict] = []
    seen: set = set()

    for _ in range(max_steps):
        resp = _ollama_chat(msgs, SCHEMAS, cfg)
        if resp is None:
            return _fallback(goal, trace)
        msg = resp.get("message", {})
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"refused": False, "plan": msg.get("content", "").strip(),
                    "trace": trace, "disclaimer": DISCLAIMER, "llm": True}
        msgs.append(msg)
        for c in calls:
            fn = c.get("function", {})
            name = fn.get("name")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args or "{}")
            key = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
            if key in seen:
                # already answered this exact call - nudge the model to finish instead of looping
                msgs.append({"role": "tool", "content": json.dumps(
                    {"note": "already called with these args; use prior result and finalise the plan"})})
                continue
            seen.add(key)
            try:
                result = dispatch(name, args)            # VALIDATED tool only
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e)}
            trace.append({"tool": name, "args": args, "result": result})
            msgs.append({"role": "tool", "content": json.dumps(result, default=str)})
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
