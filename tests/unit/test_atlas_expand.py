"""Phase 2, Step 2.1 — Writer Atlas expansion invariants.

Runs against the committed ``atlas.parquet`` deliverable (offline — no network in CI). Asserts the
pre-registered success criteria: all target families present, thousands of IS110 orthologs, every row
carries a confidence tag + >=1 source DOI, and targeting metadata is inherited (never NaN).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_ATLAS = Path(__file__).resolve().parents[2] / "pen_stack" / "atlas" / "atlas.parquet"

_EXPECTED_FAMILIES = {
    "bridge_IS110", "seek_IS1111", "CAST_VK", "serine_integrase",
    "PE_integrase", "Cas12a", "Cas9", "TnpB_Fanzor",
}


@pytest.fixture(scope="module")
def atlas() -> pd.DataFrame:
    if not _ATLAS.exists():
        pytest.skip("atlas.parquet not built (run pen_stack.atlas.expand)")
    return pd.read_parquet(_ATLAS)


def test_all_target_families_present(atlas):
    assert _EXPECTED_FAMILIES.issubset(set(atlas["family"].unique()))


def test_thousands_of_is110_orthologs(atlas):
    n = int((atlas["family"] == "bridge_IS110").sum())
    assert n >= 1000, f"expected thousands of IS110/IS1111 orthologs, got {n}"


def test_every_row_has_confidence_and_source(atlas):
    assert atlas["confidence"].notna().all()
    assert set(atlas["confidence"].unique()) <= {"measured", "inferred", "predicted"}
    n_dois = atlas["key_dois"].apply(lambda x: len([d for d in list(x) if str(d).strip()]) if x is not None else 0)
    assert int((n_dois == 0).sum()) == 0, "every atlas row must carry >=1 source DOI"


def test_targeting_metadata_inherited(atlas):
    # inherited from the WT-KB by family — never NaN (single source of truth)
    for col in ("reachability_tier", "targeting_modality", "mechanism_bucket"):
        assert atlas[col].notna().all(), f"{col} must be inherited for every atlas row"


def test_eight_curated_cores(atlas):
    cores = atlas[atlas["entry_kind"] == "curated_core"]
    assert len(cores) == 8
    assert set(cores["family"]) == _EXPECTED_FAMILIES
