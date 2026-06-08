"""WS-EP unit tests (Phase 3.2) — epistemic status + known-unknowns scope (pure-logic, CI-safe)."""
from __future__ import annotations

from pen_stack.agent import epistemic as E
from pen_stack.agent.guardrails import check_question
from pen_stack.agent.scope import is_out_of_scope, match_scope
from pen_stack.validate.out_of_scope_refusal import run as oos_run


def test_epistemic_three_tiers():
    # grounded, in-distribution, confident
    v = E.classify(grounded=True, confidence=0.9, ood_factor=1.0)
    assert v.status == E.GROUNDED_CONFIDENT
    # grounded but OOD-flagged -> extrapolating
    v = E.classify(grounded=True, confidence=0.9, ood_factor=2.0)
    assert v.status == E.GROUNDED_EXTRAPOLATING
    # not grounded -> not-computable
    assert E.classify(grounded=False).status == E.NOT_COMPUTABLE
    # abstain on low confidence -> not-computable
    assert E.classify(grounded=True, confidence=0.2).status == E.NOT_COMPUTABLE
    # out of scope -> not-computable (precedence over everything)
    assert E.classify(grounded=True, confidence=0.99, out_of_scope=True).status == E.NOT_COMPUTABLE


def test_classify_step_mapping():
    assert E.classify_step("ok", confidence=0.8, ood_factor=1.0)["epistemic_status"] == E.GROUNDED_CONFIDENT
    assert E.classify_step("refused")["epistemic_status"] == E.NOT_COMPUTABLE
    assert E.classify_step("degraded")["epistemic_status"] == E.NOT_COMPUTABLE


def test_scope_matcher_defers_known_unknowns():
    for q in ["What phenotype will this produce in the patient?",
              "Will the patient mount an immune response in vivo?",
              "Is this edit heritable and passed to offspring?",
              "What is the polygenic effect on the complex trait?"]:
        assert is_out_of_scope(q), q
        m = match_scope(q)
        assert m["out_of_scope"] and m["id"] and "does not model" in m["deferral"]


def test_scope_matcher_passes_in_scope():
    for q in ["Which writer reaches AAVS1 for a 3 kb cargo?",
              "What is the writability of CCR5 in K562?",
              "Score the off-target risk of this bridge target core."]:
        assert not is_out_of_scope(q), q


def test_out_of_scope_validator_passes():
    r = oos_run()
    assert r["passes"]
    assert r["out_of_scope"]["deferral_rate"] == 1.0
    assert r["in_scope"]["false_defer_rate"] == 0.0


def test_guardrails_check_question():
    # clinical directive -> refusal
    c = check_question("What dose should I give my patient?")
    assert c and c["kind"] == "clinical_refusal"
    # known-unknown -> deferral
    d = check_question("What long-term in-vivo durability will this have over years?")
    assert d and d["kind"] == "out_of_scope"
    # in-scope -> None
    assert check_question("Which writer reaches the albumin locus?") is None


def test_pen_agent_out_of_scope_deferral():
    from pen_stack.agent.pen_agent import plan_write_session
    r = plan_write_session("AAVS1", "safe_harbour_insertion",
                           question="What phenotype will this produce in the patient?")
    assert r["out_of_scope"] and r["abstained"] and r["no_fabrication"]
    assert not r["completed"]
    assert r["epistemic_summary"]["counts"][E.NOT_COMPUTABLE] == 1


def test_pen_agent_tags_steps_with_epistemic():
    # runs without the Phase-1 atlas -> site step refuses, but every step still carries an epistemic verdict
    from pen_stack.agent.pen_agent import plan_write_session
    r = plan_write_session("AAVS1", "safe_harbour_insertion")
    assert all("epistemic" in s for s in r["steps"])
    assert "epistemic_summary" in r and r["epistemic_summary"]["all_tagged"]
    assert r["no_fabrication"]          # the no-fabrication gate still holds
