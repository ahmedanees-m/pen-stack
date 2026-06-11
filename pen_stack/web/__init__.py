"""PEN-STACK Web Platform (v6.2) — the human surface.

A grounded co-scientist chat + every engine feature behind one typed gateway, with honest UX. The LLM narrates
and routes; the engine sources every number. Submodules:

* ``tools``  — the deterministic engine tool-runner (parse a goal, run verify/safety/immune/scope, return a
  grounded dossier) and the grounding allow-list.
* ``llm``    — the grounded co-scientist (Ollama → Nemotron → deterministic) with the grounding-guard hard gate.
* ``server`` — the FastAPI gateway (mounts the v6.1 engine surface + ``/chat``); needs the ``server`` extra.

``server`` is imported lazily (it requires FastAPI) so ``import pen_stack.web`` works on a bare install.
"""
from __future__ import annotations

from pen_stack.web.llm import grounded_reply
from pen_stack.web.tools import extract_grounded_numbers, parse_goal, run_tools

__all__ = ["grounded_reply", "run_tools", "parse_goal", "extract_grounded_numbers"]
