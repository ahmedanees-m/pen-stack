"""Framework-agnostic tool wrapper — drop PEN-STACK into any tool-calling agent (PEN-STACK v6.1, WS-EXAMPLE).

Builds tool definitions FROM the live capability manifest (so they never drift from the code) in the
OpenAI/Anthropic "tools" JSON-schema shape that LangChain, the OpenAI SDK, the Anthropic SDK, and most agent
frameworks accept. `dispatch(name, args)` calls the corresponding validated engine function in-process — every
number it returns is tool-sourced (no fabrication). `scope_tools()` exposes the known-unknowns so an agent can
check the boundary before relying on an answer.

    from examples.agent_tools import tool_specs, dispatch
    specs = tool_specs()                       # hand to your agent framework
    result = dispatch("verify_write", {"design": {...}})
"""
from __future__ import annotations

from typing import Any


def tool_specs() -> list[dict]:
    """JSON-schema tool definitions generated from the capability manifest (never hand-written)."""
    from pen_stack.api.manifest import capability_manifest
    specs = []
    for t in capability_manifest()["tools"]:
        specs.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": f"{t['summary']} (input: {t['input']} -> output: {t['output']}; fabricates: "
                               f"{t['fabricates']}).",
                "parameters": {"type": "object",
                               "properties": {"payload": {"type": "object",
                                                          "description": f"a {t['input']} object"}},
                               "required": ["payload"]},
            },
        })
    return specs


# each dispatcher routes to a validated engine entry point (numbers come only from the engine).
def _verify(p):
    from pen_stack.verify import verify
    return verify(p.get("design", p)).model_dump()


def _safety(p):
    from pen_stack.safety import safety_gate
    return safety_gate(p.get("design", p), actor="agent").model_dump()


def _immune(p):
    from pen_stack.planner.immune_profile import immune_profile
    return immune_profile(p.get("design", p))


def _generate(p):
    from pen_stack.design import generate_designs
    return generate_designs(p.get("goal"), candidates=p.get("candidates"),
                            keep=int(p.get("keep", 25)), actor="agent")


def _pareto(p):
    from pen_stack.design import pareto_front
    return pareto_front(p["designs"])


def _predict(p):
    from pen_stack.twin import predict_outcome
    return predict_outcome(p["design"], p.get("cell_state", "k562"))


def _suggest(p):
    from pen_stack.active import select_batch
    return select_batch(p["candidates"], p.get("cell_state", "k562"), {}, k=int(p.get("k", 8)))


def _session(p):
    from pen_stack.agent.co_scientist import co_scientist_session
    return co_scientist_session(p["goal"], p.get("cell_state", "k562"))


def _loop(p):
    from pen_stack.loop import run_loop
    return run_loop(p["goal"], p.get("cell_state", "k562"), candidates=p.get("candidates"))


_DISPATCH = {
    "verify_write": _verify, "safety_screen": _safety, "immune_profile": _immune,
    "generate_designs": _generate, "pareto_front": _pareto, "predict_outcome": _predict,
    "suggest_experiment": _suggest, "co_scientist_session": _session, "run_loop": _loop,
}


def dispatch(name: str, args: dict) -> Any:
    """Call a PEN-STACK tool by name with a payload dict. Numbers come only from the validated engine."""
    payload = args.get("payload", args)
    if name not in _DISPATCH:
        return {"error": f"unknown tool {name!r}", "available": sorted(_DISPATCH)}
    return _DISPATCH[name](payload)


def scope_tools() -> dict:
    """The known-unknowns an agent should check before depending on an answer."""
    from pen_stack.api.manifest import scope_manifest
    return scope_manifest()
