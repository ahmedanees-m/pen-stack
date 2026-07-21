"""Committed 1-chromosome DEMO atlas (data/demo/atlas_k562.parquet, chr19 only).

Lets a fresh clone run the safe-harbour quickstart (AAVS1 / PPP1R12C on chr19) without first fetching the
full Zenodo release. It is opt-in via PEN_ATLAS_DIR=data/demo, so the default suite - which skips cleanly
when no atlas is present - is unaffected. The full genome-wide atlas is fetched with
scripts/fetch_artifacts.sh (Zenodo).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pen_stack.atlas import crosslink as cl

_DEMO = Path(cl.__file__).resolve().parents[2] / "data" / "demo" / "atlas_k562.parquet"

pytestmark = pytest.mark.skipif(not _DEMO.exists(), reason="committed demo atlas absent")


def test_demo_atlas_is_single_chromosome_chr19():
    df = pd.read_parquet(_DEMO)
    assert set(df["chrom"].unique()) == {"chr19"}, "demo atlas must be chr19-only (a 1-chromosome demo)"
    assert len(df) > 10_000
    for col in ("chrom", "bin", "safety", "p_durable", "reachable_tier1", "writability"):
        assert col in df.columns, f"demo atlas missing loader column {col!r}"


def test_demo_atlas_serves_aavs1_quickstart(monkeypatch):
    """PEN_ATLAS_DIR=data/demo makes AAVS1 (the chr19 safe harbour) resolvable on a fresh clone."""
    monkeypatch.setenv("PEN_ATLAS_DIR", str(_DEMO.parent))
    cl.load_writability.cache_clear()
    cl._full_coverage_safety_floor.cache_clear()
    try:
        g = cl.loci_for_gene("AAVS1", "k562")  # AAVS1 -> PPP1R12C, chr19q13.42
        assert not g.empty, "AAVS1 must resolve on the chr19 demo atlas"
        assert g["writability"].max() > 0.7, "validated safe harbour must score highly writable"
        # Scope: an off-chromosome gene (CCR5 = chr3) returns empty on the chr19-only demo.
        assert cl.loci_for_gene("CCR5", "k562").empty, "chr19 demo must not answer off-chromosome genes"
    finally:
        cl.load_writability.cache_clear()
        cl._full_coverage_safety_floor.cache_clear()
