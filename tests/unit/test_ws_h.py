"""v3.1 WS-H - release + dissemination. Meta-tests that the v3.1 release artifacts are consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_is_3_1_0_release_everywhere():
    assert pen_stack.__version__ == "3.1.0"
    assert 'version = "3.1.0"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "version: 3.1.0" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")


def test_readme_updated_for_v3_1():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "version-3.1.0" in r                       # version badge bumped
    assert "Genome-Writing Bench" in r and "What is new in v3.1" in r
    assert "3.0.0a5" not in r                          # no stale version string left
    assert "tests-115" in r                            # test-count badge updated


def test_wsh_docs_exist():
    for p in ("docs/quickstart.md", "docs/positioning.md", "docs/dissemination.md",
              "benchmarks/genome_writing_bench/SUBMISSIONS.md"):
        assert (_ROOT / p).exists(), p


def test_changelog_has_3_1_0_release_entry():
    cl = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[3.1.0] -" in cl and "Genome-Writing Bench" in cl


def test_docker_compose_has_bench_service():
    dc = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "bench:" in dc and "bench/run.py" in dc


def test_all_workstream_prereg_locks_present():
    for ws in "abcdefgh":
        assert (_ROOT / f"prereg/ws_{ws}.yaml").exists(), ws
