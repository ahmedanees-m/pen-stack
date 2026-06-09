"""WS-BA unit tests (v3.3) — bench T12 rule-grounded legality + agent-uses-verifier. CI-safe."""
from __future__ import annotations

from pen_stack.validate.bench_rule_tasks import run as t12_run


def test_t12_verifier_verdict_and_reason_accuracy():
    r = t12_run()
    assert r["available"]
    assert r["verifier_verdict_accuracy"] == 1.0          # all legal/illegal verdicts correct
    assert r["verifier_reason_accuracy"] == 1.0           # every illegal case names the correct rule
    assert r["verifier_uniquely_provides_reasons"]
    assert r["no_fabrication"]


def test_t12_baseline_cannot_cite_rules():
    r = t12_run()
    # an ungrounded judge cannot name a rule -> 0 reason accuracy by construction; verifier >> baseline
    assert r["ungrounded_baseline_reason_accuracy"] == 0.0
    assert r["verifier_reason_accuracy"] > r["ungrounded_baseline_reason_accuracy"]


def test_t12_no_circular_labels():
    import yaml

    from pen_stack._resources import resource
    cfg = yaml.safe_load(resource("benchmarks/genome_writing_bench/tasks.yaml").read_text(encoding="utf-8"))
    t12 = next(t for t in cfg["tasks"] if t["id"] == "rule_grounded_legality")
    assert t12["circular"] is False
    assert cfg["version"] == "0.2.1"


def test_agent_submits_plan_to_verifier():
    # the agent attaches a verification verdict; without the Phase-1 atlas it refuses upstream (verification
    # None) but the field is always present and the no-fabrication gate holds.
    from pen_stack.agent.pen_agent import plan_write_session
    r = plan_write_session("AAVS1", "safe_harbour_insertion")
    assert "verification" in r and r["no_fabrication"]


def test_no_fabrication_audit_intact():
    from pen_stack.agent.pen_agent import no_fabrication_audit
    a = no_fabrication_audit()
    assert a["all_no_fabrication_pass"] and a["n_fabricated"] == 0
