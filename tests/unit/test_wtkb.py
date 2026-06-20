"""WT-KB schema + coverage tests (Phase 0 pre-registered success criteria)."""
from pathlib import Path

import pytest

from pen_stack.atlas.build_wtkb import build
from pen_stack.atlas.schema import Tier, WriterEntry

CURATED = Path(__file__).resolve().parents[2] / "configs" / "wtkb_curated.yaml"


def test_wtkb_builds_and_validates():
    df = build(str(CURATED)) # raises if any row fails schema/DOI rule
    assert len(df) >= 6, "Phase-0 criterion: >=6 fully-specified writer families"


def test_every_row_has_a_doi():
    df = build(str(CURATED))
    assert df["key_dois"].map(lambda d: len(d) >= 1).all()


def test_all_tiers_assigned_and_valid():
    df = build(str(CURATED))
    valid = {t.value for t in Tier}
    assert set(df["reachability_tier"]).issubset(valid)
    assert df["reachability_tier"].notna().all()


def test_at_least_two_tier1_families_for_reachability():
    # Phase-1 reachability needs Tier-1 sites recoverable for >=2 families
    df = build(str(CURATED))
    n_t1 = (df["reachability_tier"] == Tier.T1.value).sum()
    assert n_t1 >= 2


def test_missing_doi_is_rejected():
    with pytest.raises(Exception):
        WriterEntry(
            family="x", representative_system="y", mechanism_bucket="DSB_NUCLEASE",
            pfam_signature=["PF00000"], targeting_modality="RNA-guided",
            target_site_spec="t", guide_architecture="g", cargo_mechanism="templated",
            dsb_free=False, deliverability="AAV", reachability_tier="Tier1_scannable",
            reachability_constraints="c", key_dois=[], # <- violates sourcing rule
        )
