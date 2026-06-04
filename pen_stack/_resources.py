"""Resolve repo-relative resource files (configs, prereg, curated data) in both layouts.

PEN-STACK is a research pipeline: the pip wheel ships the importable library + CLI + the pure-logic tools,
while the full data pipeline (3 M-row atlases, curated configs, BigWig tracks) lives in the cloned repo and
on Zenodo, per the data policy in the README. This helper finds resource files when running from a source
checkout/sdist, and gives installed users a single escape hatch (`PEN_STACK_HOME`) to point at a checkout.
"""
from __future__ import annotations

import os
from pathlib import Path

_PKG = Path(__file__).resolve().parent          # .../pen_stack
_ENV = "PEN_STACK_HOME"


def project_root() -> Path:
    """Best guess at the project root holding configs/, prereg/, data/. `PEN_STACK_HOME` overrides."""
    env = os.environ.get(_ENV)
    if env:
        return Path(env).expanduser()
    return _PKG.parent                          # repo root in a source checkout / sdist


def resource(rel: str) -> Path:
    """Absolute path to a repo-relative resource (e.g. 'configs/cargo_polish.yaml'). Raises a clear,
    actionable error if it is not present (e.g. a bare `pip install` without `PEN_STACK_HOME` or a checkout)."""
    p = project_root() / rel
    if not p.exists():
        raise FileNotFoundError(
            f"resource {rel!r} not found at {p}. The pip wheel ships the library, not the full data/config "
            f"tree. Clone the repo for the full pipeline, or set {_ENV} to a checkout: "
            f"export {_ENV}=/path/to/pen-stack")
    return p
