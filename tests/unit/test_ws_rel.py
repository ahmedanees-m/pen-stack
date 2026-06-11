"""v4.0 WS-REL - release meta-tests: the v4.0 release artifacts are present and consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_5_6_0_everywhere():
    assert pen_stack.__version__ == "5.6.0"
    assert 'version = "5.6.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 5.6.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "version-5.6.0" in (_ROOT / "README.md").read_text(encoding="utf-8")


def test_changelog_has_5_6_0_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[5.6.0] -" in cl and "[5.5.0] -" in cl       # both kept
    assert "WS-PEG" in cl and "WS-PROFILE" in cl and "WS-CALIB" in cl


def test_readme_has_v5_6_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v5.6" in r
    assert "anti-peg" in r.lower() and "profile" in r.lower()


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
