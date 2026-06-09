"""v3.4 WS-REL - release meta-tests: the v3.4 release artifacts are present and consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_3_4_0_everywhere():
    assert pen_stack.__version__ == "3.4.0"
    assert 'version = "3.4.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 3.4.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "version-3.4.0" in (_ROOT / "README.md").read_text(encoding="utf-8")


def test_changelog_has_3_4_0_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[3.4.0] -" in cl and "[3.3.0] -" in cl       # both kept
    assert "WS-ENV" in cl and "WS-BENCH" in cl


def test_readme_has_v3_4_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v3.4" in r
    assert "environment" in r.lower()


def test_v3_4_artifacts():
    # the v3.4 artifacts: environment + bench v0.3 scorers + outcome-calibration, docs + prereg present
    from pen_stack.validate import bench_adversarial_tasks, bench_writetype_tasks, outcome_calibration  # noqa: F401
    for p in ("docs/environment.md", "pen_stack/env/policies.py",
              "prereg/ws_env.yaml", "prereg/ws_bench.yaml", "prereg/ws_cal.yaml",
              "prereg/SHA256_LOCK_ws_env.json", "prereg/SHA256_LOCK_ws_bench.json",
              "prereg/SHA256_LOCK_ws_cal.json"):
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
