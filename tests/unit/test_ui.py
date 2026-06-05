"""Headless Streamlit smoke test (v3.1). Skips unless streamlit AND the Phase-1 atlas are present (the VM
image), where it confirms the app loads and every v3.1 page renders without raising."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_HAS_ST = importlib.util.find_spec("streamlit") is not None
_ATLAS = Path(__file__).resolve().parents[2].parent / "phase_1" / "out" / "atlas_k562.parquet"
_APP = Path(__file__).resolve().parents[2] / "pen_stack" / "ui" / "app.py"

pytestmark = pytest.mark.skipif(not (_HAS_ST and _ATLAS.exists()),
                                reason="streamlit + Phase-1 atlas required (VM image)")

_V31_PAGES = ["Cargo Polish", "Multiplex risk", "Guide QC", "PEN-Agent", "Genome-Writing Bench"]


def _app():
    os.environ.setdefault("PEN_ATLAS_DIR", str(_ATLAS.parent))
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(_APP), default_timeout=90).run()


def test_app_loads_without_exception():
    at = _app()
    assert at.exception is None
    labels = at.sidebar.radio[0].options
    for pg in _V31_PAGES:
        assert pg in labels, pg


@pytest.mark.parametrize("page", _V31_PAGES)
def test_v31_page_renders(page):
    at = _app()
    at.sidebar.radio[0].set_value(page).run()
    assert at.exception is None, f"{page}: {at.exception}"
