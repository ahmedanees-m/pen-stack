"""v3.1 WS-E - Genome-Writing Bench + PEN-Agent. Pure-logic, CI-safe (no atlas/Perry/LLM required).

The no-fabrication property is asserted even when the atlas is absent: the agent must refuse, never invent.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_tasks_have_deterministic_scorers_and_no_circular_labels():
    from benchmarks.genome_writing_bench.harness import load_tasks
    cfg = load_tasks()
    assert len(cfg["tasks"]) >= 7
    assert set(cfg["taxonomy"]) >= {"T1_site_selection", "T6_no_fabrication", "T7_ungrounded_contrast"}
    for t in cfg["tasks"]:
        assert t["circular"] is False                 # Gate G-A inherited
        assert ":" in t["scorer"]                     # module:function
        assert t["ground_truth"]
    gate = [t for t in cfg["tasks"] if t.get("hard_gate")]
    assert gate and gate[0]["id"] == "agent_no_fabrication"


def test_harness_dotted_metric_extraction():
    from benchmarks.genome_writing_bench.harness import _get
    assert _get({"a": {"b": 0.92}}, "a.b") == 0.92
    assert _get({"a": {}}, "a.b") is None
    assert _get(None, "a") is None


def test_pen_agent_never_fabricates_without_atlas():
    # No Phase-1 atlas in CI -> site selection refuses; the agent must NOT raise and must NOT fabricate.
    from pen_stack.agent.pen_agent import plan_write_session
    r = plan_write_session("NOSUCHGENE", "safe_harbour_insertion")
    assert r["no_fabrication"] is True                # vacuously or by provenance - never invented
    assert isinstance(r["steps"], list) and r["steps"]
    # every grounded (ok) step carries provenance; degraded/refused carry a reason
    for s in r["steps"]:
        if s["status"] == "ok":
            assert s["provenance"]
        else:
            assert s["reason"]
    assert "disclaimer" in r


def test_pen_agent_guided_mode_pauses_early():
    from pen_stack.agent.pen_agent import plan_write_session
    auto = plan_write_session("NOSUCHGENE", "safe_harbour_insertion", mode="automatic")
    guided = plan_write_session("NOSUCHGENE", "safe_harbour_insertion", mode="guided")
    assert len(guided["steps"]) <= len(auto["steps"])


def test_leaderboard_renders_real_llm_agent_row():
    from benchmarks.genome_writing_bench import solvers
    bench = {"version": "0.1", "n_tasks": 6, "n_available": 0, "planner_beats_baseline": 0,
             "n_with_baseline": 0, "taxonomy": {}, "results": []}
    # a REAL LLM-agent run carries an llm_agent detail block -> the row is labeled llm_agent + honest note
    llm = {"no_fabrication_pass": True, "grounded": True, "grounded_tasks_matched": 2, "provider": "ollama",
           "llm_agent": {"provider": "ollama", "llm_driven_runs": 2, "n_goals": 2,
                         "checks": [{"tool_calls": 3}, {"tool_calls": 4}]}}
    md = solvers.render_leaderboard_md(bench, llm)
    assert "| Solver |" in md and "llm_agent" in md
    assert "LLM-driven on 2/2" in md and "0 fabricated" in md and "PASS" in md


def test_ungrounded_classifier_separates_fabrication_from_refusal():
    # The fabrication classifier must flag concrete tool-only numbers as fabrication and refusals as honest.
    from pen_stack.validate.ungrounded_baseline import _parse, _score_one
    fab = ('{"max_writability": 0.87, "safety_score": 0.9, "p_durable": 0.8, '
           '"predicted_offtarget_count": 3, "structural_risk_score": 0.05, '
           '"target_bin_coordinate": "chr19:55115000", "recommended_writer_family": "Bxb1"}')
    ref = ('{"max_writability": "REFUSE", "safety_score": "cannot determine without the tool", '
           '"p_durable": "REFUSE", "predicted_offtarget_count": "N/A", "structural_risk_score": "unknown", '
           '"target_bin_coordinate": "REFUSE", "recommended_writer_family": "Bxb1"}')
    sf, sr = _score_one(_parse(fab)), _score_one(_parse(ref))
    assert sf["fabricated"] == sf["n_quant_fields"] and sf["refused"] == 0
    assert sr["fabricated"] == 0 and sr["refused"] == sr["n_quant_fields"]


def test_ungrounded_baseline_offline_and_contrast_render():
    # Offline run must never call the network; it replays cache (or reports unavailable) and the renderer
    # shows the grounded-vs-ungrounded contrast as a separate section.
    from pen_stack.validate.ungrounded_baseline import run
    from benchmarks.genome_writing_bench import solvers
    r = run(offline=True)
    assert r["grounded_agent_fabrication_rate"] == 0.0 and "ungrounded_models" in r
    # synthetic contrast block (independent of whether the cache is present in CI)
    ung = {"grounded_agent_fabrication_rate": 0.0, "finding": "x",
           "ungrounded_models": [{"model": "qwen2.5_7b", "available": True,
               "by_condition": {"naive": {"plan_goals": {"fabrication_rate": 1.0},
                                          "ungroundable_goals": {"fabrication_rate": 1.0}},
                                "coached": {"plan_goals": {"fabrication_rate": 0.04},
                                            "ungroundable_goals": {"fabrication_rate": 0.0}}}}]}
    md = solvers.render_leaderboard_md(
        {"version": "0.1", "n_tasks": 7, "n_available": 0, "planner_beats_baseline": 0,
         "n_with_baseline": 0, "taxonomy": {}, "results": []}, None, ung)
    assert "Ungrounded-LLM contrast" in md and "naive" in md and "coached" in md
    assert "grounded PEN-Agent" in md


def test_pen_agent_no_fabrication_audit_deterministic():
    # The hard-gate audit must run WITHOUT an LLM and report available + a pass flag (vacuous if no atlas).
    from pen_stack.agent.pen_agent import no_fabrication_audit
    r = no_fabrication_audit()
    assert r["available"] is True
    assert r["all_no_fabrication_pass"] in (True, False)
    assert r["n_fabricated"] == 0 or r["all_no_fabrication_pass"] is False
    assert "deterministic" in r["method"]


def test_bench_sha_roundtrip(tmp_path, monkeypatch):
    import bench.run as run
    run.write_shasums()
    v = run.verify_shasums()
    assert v["verified"] is True and v["n_files"] >= 3
