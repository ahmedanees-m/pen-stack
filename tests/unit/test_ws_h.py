"""v3.1 WS-H - release + dissemination. Meta-tests that the v3.1 release artifacts are consistent."""
from __future__ import annotations

from pathlib import Path

import pen_stack

_ROOT = Path(__file__).resolve().parents[2]


def test_version_consistent_everywhere():
    # consistency, not a pinned value (the version bumps per cycle): __init__ == pyproject == CITATION
    v = pen_stack.__version__
    assert v.split(".")[0] in {"3", "4"}
    assert f'version = "{v}"' in (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f"version: {v}" in (_ROOT / "CITATION.cff").read_text(encoding="utf-8")


def test_readme_version_badge_matches():
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert f"version-{pen_stack.__version__}" in r     # version badge matches the package version
    assert "Genome-Writing Bench" in r
    assert "3.0.0a5" not in r                          # no stale alpha version string left


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


def test_pypi_packaging_ready():
    # build + publish plumbing for the PyPI release
    r = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "pypi/v/pen-stack" in r                                # PyPI badge present
    assert (_ROOT / ".github/workflows/publish.yml").exists()     # automated publish workflow
    assert (_ROOT / "MANIFEST.in").exists() and (_ROOT / "docs/RELEASING.md").exists()
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "Development Status :: 4 - Beta" in pp and "Issues =" in pp


def test_resource_resolver_finds_and_errors_clearly():
    from pen_stack._resources import project_root, resource
    assert (project_root() / "pen_stack").exists()                # repo root in a source checkout
    assert resource("configs/cargo_polish.yaml").exists()         # finds a real resource
    import pytest
    with pytest.raises(FileNotFoundError, match="PEN_STACK_HOME"):
        resource("configs/does_not_exist_xyz.yaml")              # clear, actionable error
