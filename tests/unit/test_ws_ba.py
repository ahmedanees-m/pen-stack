"""WS-BA unit tests (Phase 3.2) - bench v0.2 trust tasks + uncertainty-aware agent. Pure-logic, CI-safe."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]      # repo root (holds benchmarks/, bench/) - not an installed pkg
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.genome_writing_bench import harness, solvers  # noqa: E402
from pen_stack.validate import bench_trust_tasks as B  # noqa: E402


def test_bench_is_v0_2_with_trust_tasks():
    cfg = harness.load_tasks()
    assert cfg["version"] == "0.2"
    ids = {t["id"] for t in cfg["tasks"]}
    assert {"calibration_coverage", "selective_prediction_usefulness",
            "ood_honesty", "out_of_scope_refusal"} <= ids
    # every task is non-circular
    assert all(t["circular"] is False for t in cfg["tasks"])


def test_ci_safe_trust_tasks_run():
    # T10 + T11 are deterministic / pure-logic -> always available, beat the over-confident baseline
    o = B.ood_honesty()
    assert o["available"] and o["honest_on_ood"]
    assert o["ood_flag_rate"] > o["overconfident_agent_ood_flag_rate"]
    s = B.out_of_scope()
    assert s["available"] and s["deferral_rate"] == 1.0
    assert s["deferral_rate"] > s["ungrounded_no_scope_deferral_rate"]
    assert s["false_defer_rate"] == 0.0


def test_harness_runs_ci_safe_trust_tasks():
    r = harness.run_bench(["ood_honesty", "out_of_scope_refusal"])
    assert r["version"] == "0.2" and r["n_available"] == 2
    # the uncertainty-aware agent beats the over-confident baseline on both
    for x in r["results"]:
        assert x["planner_score"] > x["baseline_score"]


def test_leaderboard_renders_trust_contrast():
    bench = harness.run_bench(["ood_honesty", "out_of_scope_refusal"])
    md = solvers.render_leaderboard_md(bench)
    assert "Trust tasks (T8-T11)" in md
    assert "v0.2" in md
    assert "calibration + scope-awareness separate" in md


def test_no_fabrication_gate_still_passes():
    from pen_stack.agent.pen_agent import no_fabrication_audit
    r = no_fabrication_audit()
    assert r["all_no_fabrication_pass"] and r["n_fabricated"] == 0


def test_agent_emits_confidence_and_epistemic():
    from pen_stack.agent.pen_agent import plan_write_session
    r = plan_write_session("AAVS1", "safe_harbour_insertion")
    assert "plan_confidence" in r and "abstained" in r and "epistemic_summary" in r
    assert all("epistemic" in s for s in r["steps"])
