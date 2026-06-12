"""v4.0 WS-REL - release meta-tests: the v4.0 release artifacts are present and consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_6_3_0_everywhere():
    assert pen_stack.__version__ == "6.3.0"
    assert 'version = "6.3.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 6.3.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "version-6.3.0" in (_ROOT / "README.md").read_text(encoding="utf-8")


def test_v6_3_artifacts():
    # the v6.3 artifacts: the hybrid co-scientist (4-lane router + metric guide + facts + hybrid llm + preregs)
    from pen_stack.web.guide import metric_guide, pen_stack_facts  # noqa: F401
    from pen_stack.web.llm import grounded_reply  # noqa: F401
    from pen_stack.web.router import classify, pen_stack_angles  # noqa: F401
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[6.3.0] -" in cl and "WS-HYBRID" in cl
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v6.3" in r and "general knowledge" in r.lower()
    for p in ("pen_stack/web/router.py", "pen_stack/web/guide.py", "configs/metric_guide.yaml",
              "prereg/ws_hybrid.yaml", "prereg/SHA256_LOCK_ws_hybrid.json"):
        assert (_ROOT / p).exists(), p


def test_v6_2_artifacts():
    # the v6.2 artifacts: the Web Platform (grounded co-scientist + honest-UX frontend + Docker self-host + preregs)
    from pen_stack.web import extract_grounded_numbers, grounded_reply, run_tools  # noqa: F401
    from pen_stack.web.llm import _deterministic_narrate, _enforce_grounding  # noqa: F401
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[6.2.0] -" in cl and "WS-CHAT" in cl and "WS-FRONTEND" in cl
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v6.2" in r and "grounding guard" in r.lower()
    for p in ("pen_stack/web/__init__.py", "pen_stack/web/tools.py", "pen_stack/web/llm.py",
              "pen_stack/web/server.py", "tests/unit/test_ws_chat.py", "docker/web.Dockerfile",
              "web/package.json", "web/src/App.jsx", "web/src/components/ConfidenceBand.jsx",
              "web/src/pages/CoScientist.jsx", "web/README.md",
              "prereg/ws_chat.yaml", "prereg/SHA256_LOCK_ws_chat.json",
              "prereg/ws_frontend.yaml", "prereg/SHA256_LOCK_ws_frontend.json"):
        assert (_ROOT / p).exists(), p


def test_grounding_guard_strikes_ungrounded_numbers():
    # the central v6.2 gate, asserted at release: a reply never carries a number absent from the tool results
    from pen_stack.web.llm import _enforce_grounding, ungrounded_numbers
    grounded = {"0.28", "1", "4500"}
    cleaned = _enforce_grounding("conf 0.28 but titer 9.99 at 4500 bp", grounded)
    assert "9.99" not in cleaned and "[unverified]" in cleaned
    assert ungrounded_numbers(cleaned, grounded) == []


def test_v6_1_artifacts():
    # the v6.1 artifacts: the AI integration surface (manifests + endpoints + MCP resources + examples + preregs)
    from examples.agent_tools import dispatch, tool_specs  # noqa: F401
    from pen_stack.api import capability_manifest, scope_manifest
    cap, sc = capability_manifest(), scope_manifest()
    assert cap["tools"] and all(t["fabricates"] is False for t in cap["tools"])
    assert sc["known_unknowns"] and sc["oracle_scope_cards"] and sc["policy"]
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[6.1.0] -" in cl and "WS-MANIFEST" in cl
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v6.1" in r
    for p in ("pen_stack/api/manifest.py", "examples/external_agent.py", "examples/mcp_client.py",
              "examples/agent_tools.py", "prereg/ws_manifest.yaml", "prereg/SHA256_LOCK_ws_manifest.json",
              "prereg/ws_openapi.yaml", "prereg/SHA256_LOCK_ws_openapi.json", "prereg/ws_mcp.yaml",
              "prereg/SHA256_LOCK_ws_mcp.json"):
        assert (_ROOT / p).exists(), p


def test_v6_0_0_first_stable_graduation():
    # 1.0 - First Stable: Production/Stable classifier + a documented API stability / deprecation policy
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "Development Status :: 5 - Production/Stable" in pp
    assert (_ROOT / "docs/STABILITY.md").exists()
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[6.0.0] -" in cl and "First Stable" in cl
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "1.0 — First Stable" in r or "1.0 - First Stable" in r


def test_changelog_has_5_13_0_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[5.13.0] -" in cl and "[5.12.0] -" in cl       # both kept
    assert "WS-CHALLENGE" in cl and "WS-COSCI2" in cl and "WS-ADOPT" in cl


def test_readme_has_v5_13_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v5.13" in r
    assert "challenge" in r.lower() and "co-scientist" in r.lower()


def test_v5_13_artifacts():
    # the v5.13 artifacts: the Genome-Writing Challenge + the co-scientist over the loop + integrations + preregs
    from benchmarks.genome_writing_challenge.harness import (  # noqa: F401
        Submission,
        evaluate,
        reference_submission,
    )
    from pen_stack.agent.co_scientist import co_scientist_session  # noqa: F401
    for p in ("benchmarks/genome_writing_challenge/harness.py", "benchmarks/genome_writing_challenge/run.py",
              "benchmarks/genome_writing_challenge/README.md", "benchmarks/genome_writing_challenge/SUBMISSIONS.md",
              "docs/challenge.md", "docs/co_scientist_loop.md", "docs/integrations.md",
              "prereg/ws_challenge.yaml", "prereg/SHA256_LOCK_ws_challenge.json", "prereg/ws_cosci2.yaml",
              "prereg/SHA256_LOCK_ws_cosci2.json"):
        assert (_ROOT / p).exists(), p


def test_v5_12_artifacts():
    # the v5.12 artifacts: the closed loop (cycle + drift + continual) + bench + docs + preregs
    from pen_stack.loop import continual_update, detect_drift, run_loop  # noqa: F401
    from pen_stack.validate.closed_loop import run as _cl_bench  # noqa: F401
    for p in ("pen_stack/loop/__init__.py", "pen_stack/loop/cycle.py", "pen_stack/loop/drift.py",
              "pen_stack/loop/continual.py", "pen_stack/validate/closed_loop.py", "docs/closed_loop.md",
              "docs/autonomy.md", "prereg/ws_loop.yaml", "prereg/SHA256_LOCK_ws_loop.json",
              "prereg/ws_continual.yaml", "prereg/SHA256_LOCK_ws_continual.json", "prereg/ws_drift.yaml",
              "prereg/SHA256_LOCK_ws_drift.json"):
        assert (_ROOT / p).exists(), p


def test_v5_11_artifacts():
    # the v5.11 artifacts: the build interface (protocol + ingest + simlab) + bench + preregs
    from pen_stack.build import (  # noqa: F401
        ProtocolExportError,
        export_protocol,
        ingest_result,
        run_simulated,
    )
    from pen_stack.validate.protocol_safety import run as _ps_bench  # noqa: F401
    for p in ("pen_stack/build/__init__.py", "pen_stack/build/protocol.py", "pen_stack/build/ingest.py",
              "pen_stack/build/simlab.py", "pen_stack/validate/protocol_safety.py", "docs/build_interface.md",
              "prereg/ws_proto.yaml", "prereg/SHA256_LOCK_ws_proto.json", "prereg/ws_ingest.yaml",
              "prereg/SHA256_LOCK_ws_ingest.json", "prereg/ws_simlab.yaml", "prereg/SHA256_LOCK_ws_simlab.json"):
        assert (_ROOT / p).exists(), p


def test_v5_10_artifacts():
    # the v5.10 artifacts: the experiment designer (acquire + design + validate) + bench + preregs
    from pen_stack.active import (  # noqa: F401
        acquisition_score,
        expected_information_gain,
        immune_voi,
        retrospective_active_learning,
        select_batch,
    )
    from pen_stack.validate.experiment_design import run as _ed_bench  # noqa: F401
    for p in ("pen_stack/active/__init__.py", "pen_stack/active/acquire.py", "pen_stack/active/design.py",
              "pen_stack/active/validate.py", "pen_stack/validate/experiment_design.py",
              "docs/experiment_design.md", "prereg/ws_acq.yaml", "prereg/SHA256_LOCK_ws_acq.json",
              "prereg/ws_aldesign.yaml", "prereg/SHA256_LOCK_ws_aldesign.json", "prereg/ws_alvalidate.yaml",
              "prereg/SHA256_LOCK_ws_alvalidate.json"):
        assert (_ROOT / p).exists(), p


def test_v5_9_artifacts():
    # the v5.9 artifacts: the digital twin (vcell oracle + mechanistic + outcome + calibrate) + bench + preregs
    from pen_stack.oracles.vcell import predict_response  # noqa: F401
    from pen_stack.twin import calibrate_outcome, cassette_expression, predict_outcome  # noqa: F401
    from pen_stack.validate.outcome_prediction import run as _twin_bench  # noqa: F401
    for p in ("pen_stack/oracles/vcell.py", "pen_stack/twin/__init__.py", "pen_stack/twin/mechanistic.py",
              "pen_stack/twin/outcome.py", "pen_stack/twin/calibrate.py",
              "pen_stack/validate/outcome_prediction.py", "docs/digital_twin.md",
              "prereg/ws_vcell.yaml", "prereg/SHA256_LOCK_ws_vcell.json", "prereg/ws_mech.yaml",
              "prereg/SHA256_LOCK_ws_mech.json", "prereg/ws_outcome.yaml", "prereg/SHA256_LOCK_ws_outcome.json",
              "prereg/ws_twincal.yaml", "prereg/SHA256_LOCK_ws_twincal.json"):
        assert (_ROOT / p).exists(), p
    # the v5.9 scope cards for the virtual-cell oracle are registered
    import yaml
    cards = yaml.safe_load((_ROOT / "configs/oracles/scope_cards.yaml").read_text(encoding="utf-8"))["oracles"]
    assert "state" in cards and "scgpt" in cards and cards["state"]["family"] == "vcell"


def test_v5_8_artifacts():
    # the v5.8 artifacts: the generative designer (space/generate/pareto) + live orchestrator + bench + preregs
    from pen_stack.agent.orchestrator_live import orchestrate  # noqa: F401
    from pen_stack.design import candidate_space, generate_designs, neg_immune_risk, pareto_front  # noqa: F401
    from pen_stack.validate.generative_design import run as _gen_bench  # noqa: F401
    for p in ("pen_stack/design/__init__.py", "pen_stack/design/space.py", "pen_stack/design/generate.py",
              "pen_stack/design/pareto.py", "pen_stack/agent/orchestrator_live.py",
              "pen_stack/validate/generative_design.py", "docs/generative_design.md",
              "prereg/ws_gen.yaml", "prereg/SHA256_LOCK_ws_gen.json", "prereg/ws_pareto.yaml",
              "prereg/SHA256_LOCK_ws_pareto.json", "prereg/ws_orch.yaml", "prereg/SHA256_LOCK_ws_orch.json"):
        assert (_ROOT / p).exists(), p


def test_v5_7_artifacts():
    # the v5.7 artifacts: the Guardian safety gate (registry/screen/policy/gate/audit/redteam) +
    # Verdict.safety + bench safety_screening + docs + preregs
    from pen_stack.safety import SafetyVerdict, safety_gate, screen_design, verify_chain  # noqa: F401
    from pen_stack.validate.safety_screening import run as _safety_bench  # noqa: F401
    from pen_stack.verify.schema import Verdict
    assert "safety" in Verdict.model_fields
    for p in ("pen_stack/safety/registry.py", "pen_stack/safety/screen.py", "pen_stack/safety/policy.py",
              "pen_stack/safety/gate.py", "pen_stack/safety/audit.py", "pen_stack/safety/redteam.py",
              "configs/safety/hazard_registry.yaml", "configs/safety/policy.yaml", "configs/safety/probes.yaml",
              "pen_stack/validate/safety_screening.py", "docs/responsible_use.md", "docs/biosecurity.md",
              "prereg/ws_screen.yaml", "prereg/SHA256_LOCK_ws_screen.json", "prereg/ws_policy.yaml",
              "prereg/SHA256_LOCK_ws_policy.json", "prereg/ws_redteam.yaml",
              "prereg/SHA256_LOCK_ws_redteam.json"):
        assert (_ROOT / p).exists(), p


def test_v5_6_artifacts():
    # the v5.6 artifacts: anti-PEG oracle + calibration + unified profile + Verdict.immune_profile + preregs
    from pen_stack.planner.antipeg_oracle import antipeg_oracle  # noqa: F401
    from pen_stack.planner.immune_profile import immune_profile  # noqa: F401
    from pen_stack.validate.immune_calibration import calibrate_axis  # noqa: F401
    for p in ("pen_stack/planner/antipeg_oracle.py", "configs/antipeg.yaml",
              "pen_stack/planner/immune_profile.py", "pen_stack/validate/immune_calibration.py",
              "prereg/ws_peg.yaml", "prereg/SHA256_LOCK_ws_peg.json", "prereg/ws_calib.yaml",
              "prereg/SHA256_LOCK_ws_calib.json", "prereg/ws_profile.yaml",
              "prereg/SHA256_LOCK_ws_profile.json"):
        assert (_ROOT / p).exists(), p


def test_v5_5_artifacts():
    # the v5.5 artifacts: anti-vector seroprevalence oracle + curated table + scope card + prereg
    from pen_stack.planner.seroprevalence_oracle import computed_preexisting_score, seroprevalence_oracle  # noqa: F401,E501
    for p in ("pen_stack/planner/seroprevalence_oracle.py", "configs/seroprevalence.yaml",
              "prereg/ws_seroprev.yaml", "prereg/SHA256_LOCK_ws_seroprev.json"):
        assert (_ROOT / p).exists(), p


def test_v5_4_artifacts():
    # the v5.4 artifacts: computed innate-sensing scorer + scope card + prereg
    from pen_stack.planner.innate_sensing import computed_innate_score, innate_sensing  # noqa: F401
    for p in ("pen_stack/planner/innate_sensing.py", "prereg/ws_innate.yaml",
              "prereg/SHA256_LOCK_ws_innate.json"):
        assert (_ROOT / p).exists(), p


def test_v5_3_artifacts():
    # the v5.3 artifacts: computed capsid epitope oracle + committed summary + sequences + scope card + prereg
    from pen_stack.planner.capsid_epitope_oracle import capsid_epitope_oracle, computed_capsid_immune_score  # noqa: F401,E501
    for p in ("pen_stack/planner/capsid_epitope_oracle.py", "configs/capsid_epitope_oracle.yaml",
              "configs/capsid_sequences.fasta", "scripts/p53_build_epitope_oracle.py",
              "prereg/ws_epitope.yaml", "prereg/SHA256_LOCK_ws_epitope.json"):
        assert (_ROOT / p).exists(), p


def test_v5_2_artifacts():
    # the v5.2 artifacts: computed genotoxicity oracle + committed summary + scope card + prereg
    from pen_stack.planner.genotoxicity_oracle import computed_genotox_score, genotoxicity_oracle  # noqa: F401
    for p in ("pen_stack/planner/genotoxicity_oracle.py", "configs/genotoxicity_oracle.yaml",
              "scripts/p52_build_genotox_oracle.py", "prereg/ws_genotox.yaml",
              "prereg/SHA256_LOCK_ws_genotox.json"):
        assert (_ROOT / p).exists(), p


def test_v5_1_artifacts():
    # the v5.1 artifacts: delivery-immunology planner + per-vehicle immune profiles + verify surfacing
    from pen_stack.planner.delivery_immunology import recommend_delivery, safety_efficacy_profile  # noqa: F401
    for p in ("pen_stack/planner/delivery_immunology.py", "prereg/ws_immune.yaml",
              "prereg/SHA256_LOCK_ws_immune.json"):
        assert (_ROOT / p).exists(), p


def test_readme_has_v5_0_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v5.0" in r
    assert "co-scientist" in r.lower()


def test_v5_0_artifacts():
    # the v5.0 artifacts: co-scientist (plan/multi/crit/scope/cite/gen) + bench reference solver
    from pen_stack.agent.cite import cited_rationale, generalise  # noqa: F401
    from pen_stack.agent.co_scientist import critique_and_revise, propose_strategies, scope_ledger  # noqa: F401
    from pen_stack.validate import bench_coscientist_tasks  # noqa: F401
    for p in ("docs/co_scientist.md", "pen_stack/agent/co_scientist.py", "pen_stack/agent/cite.py",
              "prereg/ws_plan.yaml", "prereg/ws_crit.yaml", "prereg/ws_cite.yaml",
              "prereg/SHA256_LOCK_ws_plan.json", "prereg/SHA256_LOCK_ws_crit.json",
              "prereg/SHA256_LOCK_ws_cite.json"):
        assert (_ROOT / p).exists(), p


def test_no_fabrication_under_full_reasoning_stack():
    # the central v5.0 gate, asserted at release: the matured co-scientist never fabricates
    from pen_stack.validate.bench_coscientist_tasks import run
    rep = run()
    assert rep["co_scientist_grounded_rate"] == 1.0 and rep["no_fabrication"] is True


def test_readme_has_v4_5_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v4.5" in r
    assert "world-model" in r.lower() or "knowledge graph" in r.lower()


def test_v4_5_artifacts():
    # the v4.5 artifacts: world-model graph + gated ingest + cell-type coverage + graph bench
    from pen_stack.graph import build_graph  # noqa: F401
    from pen_stack.graph.cell_types import coverage_card  # noqa: F401
    from pen_stack.graph.ingest import gate_admit  # noqa: F401
    from pen_stack.validate import bench_graph_tasks  # noqa: F401
    for p in ("docs/world_model.md", "configs/cell_types.yaml", "pen_stack/graph/schema.py",
              "prereg/ws_graph.yaml", "prereg/ws_mon.yaml", "prereg/ws_ct.yaml", "prereg/ws_ba_v45.yaml",
              "prereg/SHA256_LOCK_ws_graph.json", "prereg/SHA256_LOCK_ws_mon.json",
              "prereg/SHA256_LOCK_ws_ct.json", "prereg/SHA256_LOCK_ws_ba_v45.json"):
        assert (_ROOT / p).exists(), p


def test_v4_0_artifacts():
    # the v4.0 artifacts: oracle mesh + writer-verification + mesh atlas, docs + prereg present
    from pen_stack.atlas import writer_verify  # noqa: F401
    from pen_stack.oracles import OracleResult  # noqa: F401
    from pen_stack.wgenome import mesh_features  # noqa: F401
    for p in ("docs/oracles.md", "docs/writer_verification.md",
              "configs/oracles/scope_cards.yaml", "pen_stack/oracles/schema.py",
              "prereg/ws_o.yaml", "prereg/ws_wv.yaml", "prereg/ws_atlas.yaml",
              "prereg/SHA256_LOCK_ws_o.json", "prereg/SHA256_LOCK_ws_wv.json",
              "prereg/SHA256_LOCK_ws_atlas.json"):
        assert (_ROOT / p).exists(), p


def test_v3_3_verifier_and_rules():
    # the v3.3 artifacts: rule base + verifier importable, docs + prereg present, bench bumped
    from pen_stack.rules import load_ruleset
    from pen_stack.verify import verify  # noqa: F401
    assert len(load_ruleset().rules) >= 9
    for p in ("docs/verify.md", "docs/rules.md", "docs/delivery.md",
              "prereg/ws_r.yaml", "prereg/ws_v.yaml", "configs/delivery_vehicles.yaml"):
        assert (_ROOT / p).exists(), p


def test_v3_2_docs_exist():
    for p in ("docs/uncertainty.md", "docs/scope.md", "docs/mechanistic_constraints.md", "docs/BACKLOG.md"):
        assert (_ROOT / p).exists(), p


def test_v3_2_prereg_locks_present():
    for ws in ("uq", "ep", "mc", "ba"):
        assert (_ROOT / f"prereg/ws_{ws}.yaml").exists(), ws
        assert (_ROOT / f"prereg/SHA256_LOCK_ws_{ws}.json").exists(), ws


def test_bench_is_v0_3():
    import yaml
    cfg = yaml.safe_load((_ROOT / "benchmarks/genome_writing_bench/tasks.yaml").read_text(encoding="utf-8"))
    assert cfg["version"] >= "0.3"
    ids = {t["id"] for t in cfg["tasks"]}
    assert {"multi_write_type_legality", "adversarial_robustness", "rule_grounded_legality"} <= ids


def test_env_extra_declared():
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gymnasium" in pp and "env = [" in pp

# NOTE: manuscripts/ (incl. the M-UQ note + M1/M2 updates) is intentionally gitignored - drafts live on the
# Drive and in the phase_3.2/ws_rel deposit, not in the public repo - so the release test does NOT assert
# their presence (they are absent in a clean CI checkout / a clone, by design).
