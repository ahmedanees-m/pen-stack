"""v3.2 WS-REL - release meta-tests: the v3.2 release artifacts are present and consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_3_3_0_everywhere():
    assert pen_stack.__version__ == "3.3.0"
    assert 'version = "3.3.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 3.3.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "version-3.3.0" in (_ROOT / "README.md").read_text(encoding="utf-8")


def test_changelog_has_3_3_0_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[3.3.0] -" in cl and "[3.2.0] -" in cl       # both kept
    assert "WS-R" in cl and "WS-V" in cl


def test_readme_has_v3_3_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v3.3" in r
    assert "verify(design)" in r or "verify_write" in r


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


def test_bench_is_v0_2_1():
    import yaml
    cfg = yaml.safe_load((_ROOT / "benchmarks/genome_writing_bench/tasks.yaml").read_text(encoding="utf-8"))
    assert cfg["version"] == "0.2.1"
    assert any(t["id"] == "rule_grounded_legality" for t in cfg["tasks"])


def test_env_extra_declared():
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gymnasium" in pp and "env = [" in pp

# NOTE: manuscripts/ (incl. the M-UQ note + M1/M2 updates) is intentionally gitignored - drafts live on the
# Drive and in the phase_3.2/ws_rel deposit, not in the public repo - so the release test does NOT assert
# their presence (they are absent in a clean CI checkout / a clone, by design).
