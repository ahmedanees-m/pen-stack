"""v3.2 WS-REL - release meta-tests: the v3.2 release artifacts are present and consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_3_2_0_everywhere():
    assert pen_stack.__version__ == "3.2.0"
    assert 'version = "3.2.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 3.2.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "version-3.2.0" in (_ROOT / "README.md").read_text(encoding="utf-8")


def test_changelog_has_3_2_0_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[3.2.0] -" in cl
    assert "WS-UQ" in cl and "WS-EP" in cl and "WS-MC" in cl and "WS-BA" in cl


def test_readme_has_v3_2_section():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "What is new in v3.2" in r
    assert "Genome-Writing Bench v0.2" in r


def test_v3_2_docs_exist():
    for p in ("docs/uncertainty.md", "docs/scope.md", "docs/mechanistic_constraints.md", "docs/BACKLOG.md"):
        assert (_ROOT / p).exists(), p


def test_v3_2_prereg_locks_present():
    for ws in ("uq", "ep", "mc", "ba"):
        assert (_ROOT / f"prereg/ws_{ws}.yaml").exists(), ws
        assert (_ROOT / f"prereg/SHA256_LOCK_ws_{ws}.json").exists(), ws


def test_bench_is_v0_2():
    import yaml
    cfg = yaml.safe_load((_ROOT / "benchmarks/genome_writing_bench/tasks.yaml").read_text(encoding="utf-8"))
    assert cfg["version"] == "0.2"


def test_env_extra_declared():
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "gymnasium" in pp and "env = [" in pp

# NOTE: manuscripts/ (incl. the M-UQ note + M1/M2 updates) is intentionally gitignored - drafts live on the
# Drive and in the phase_3.2/ws_rel deposit, not in the public repo - so the release test does NOT assert
# their presence (they are absent in a clean CI checkout / a clone, by design).
