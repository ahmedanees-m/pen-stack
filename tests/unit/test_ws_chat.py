"""WS-CHAT unit tests (Phase 6.2, the grounded co-scientist).

The hard gate (pre-registered): **no numeric claim in a reply is absent from the tool results.** These tests are
pure-Python and CI-safe — they never call a live LLM. They exercise:
  * the engine tool-runner produces a grounded dossier (legality/safety/immune/scope) for the example goal;
  * the grounding guard strikes any number a model invents that is not in the engine's allow-list;
  * the deterministic narrator's reply contains ONLY grounded numbers (the LLM-offline path);
  * a mock LLM that injects a fabricated titer cannot get that number past the guard;
  * the public `grounded_reply` falls back to deterministic when no LLM is reachable.
"""
from __future__ import annotations

import pytest

from pen_stack.web.llm import (
    _deterministic_narrate,
    _enforce_grounding,
    grounded_reply,
    ungrounded_numbers,
)
from pen_stack.web.tools import extract_grounded_numbers, parse_goal, run_tools

_GOAL = "durably express Factor IX in adult liver using AAV, 4.5 kb cargo"


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))
    monkeypatch.setenv("PEN_STACK_NO_LLM", "1")          # never reach a live LLM in CI


def test_parse_goal_picks_a_runnable_design():
    d = parse_goal(_GOAL)
    assert d["delivery_vehicle"] == "AAV_single"
    assert d["edit_intent"] == "high_durability_insertion"
    assert d["cargo_bp"] == 4500                          # "4.5 kb" -> 4500 bp


def test_run_tools_returns_a_grounded_dossier():
    tr = run_tools(_GOAL)
    assert tr["verdict"]["legal"] is True
    assert tr["safety"]["decision"] in {"clear", "flag", "escalate", "refuse"}
    assert set(tr["immune_profile"]["axes"]) >= {"genotoxicity", "cd8_epitope", "innate"}
    assert tr["immune_profile"]["collapsed_score"] is None       # per-axis, never fused
    assert "disclaimer" in tr


def test_grounding_guard_strikes_an_invented_number():
    grounded = {"0.28", "1", "4500"}
    text = "Confidence is 0.28 and the titer is 9.99 with 4500 bp cargo."
    out = _enforce_grounding(text, grounded)
    assert "0.28" in out and "4500" in out               # grounded numbers survive
    assert "9.99" not in out and "[unverified]" in out   # the invented titer is struck


def test_deterministic_reply_has_only_grounded_numbers():
    tr = run_tools(_GOAL)
    grounded = extract_grounded_numbers(tr)
    reply = _deterministic_narrate(tr)
    assert ungrounded_numbers(reply, grounded) == []     # the invariant: no ungrounded number in the reply


def test_mock_llm_cannot_smuggle_a_fabricated_titer():
    """A model that invents '1e6 vg' / '73%' is caught: after the guard those numbers are gone."""
    tr = run_tools(_GOAL)
    grounded = extract_grounded_numbers(tr)
    fabricated = "You will achieve 73% expression at a dose of 1000000 vector genomes."
    cleaned = _enforce_grounding(fabricated, grounded)
    assert "73%" not in cleaned and "1000000" not in cleaned
    assert ungrounded_numbers(cleaned, grounded) == []


def test_grounded_reply_falls_back_to_deterministic_when_no_llm():
    out = grounded_reply(_GOAL)
    assert out["backend"] == "deterministic" and out["grounded"] is True
    grounded = extract_grounded_numbers(out["tool_results"])
    assert ungrounded_numbers(out["reply"], grounded) == []


def test_chat_screens_a_hazardous_goal():
    """The chat must biosecurity-screen the user's stated goal: a hazardous request is NOT silently 'clear'
    (parse_goal carries the plain-language goal as the cargo function the Guardian screens)."""
    assert run_tools("express a ricin toxin in human cells with AAV")["safety"]["decision"] != "clear"
    assert run_tools(_GOAL)["safety"]["decision"] == "clear"          # a benign goal still clears


def test_gateway_chat_requires_a_message():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from pen_stack.web.server import app
    c = TestClient(app)
    assert c.post("/chat", json={"allow_llm": False}).status_code == 422       # missing message -> 422 not 500
    assert c.post("/chat", json={"message": "   ", "allow_llm": False}).status_code == 422
    r = c.post("/chat", json={"message": "express a ricin toxin in human cells", "allow_llm": False})
    assert r.status_code == 200 and r.json()["tool_results"]["safety"]["decision"] != "clear"
