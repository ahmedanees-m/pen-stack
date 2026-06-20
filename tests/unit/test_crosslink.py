"""Phase 2, Step 2.5 - Writer Atlas <-> Writable Genome cross-link.

Pre-registered criterion: cross-link queries return correct sets on a held-out check (the bridge family
<-> bridge-reachable loci, and a validated safe harbour scores highly writable AND bridge-reachable).
Skips cleanly when the Phase-1 writability atlas (fetched-not-committed) is absent.
"""
from __future__ import annotations

import pytest

from pen_stack.atlas import crosslink as cl


def _have(ct: str) -> bool:
    try:
        cl.writability_path(ct)
        return True
    except FileNotFoundError:
        return False


pytestmark = pytest.mark.skipif(not _have("k562"), reason="Phase-1 atlas_k562.parquet not present")


def test_bridge_family_reaches_loci_ranked():
    top = cl.loci_for_writer("bridge_IS110", "k562", top=5)
    assert len(top) == 5
    # ranked by writability, descending
    assert top["writability"].is_monotonic_decreasing
    # every returned locus is actually bridge-reachable
    assert top["reachable_tier1"].str.contains("bridge_IS110").all()


def test_aavs1_is_writable_and_bridge_reachable():
    # AAVS1 = PPP1R12C, chr19 ~55,090,914 -> bin 55090
    w = cl.writers_for_locus("chr19", 55090, "k562")
    assert not w.empty
    assert "bridge_IS110" in set(w["family"])
    assert w["locus_writability"].iloc[0] > 0.7 # validated safe harbour -> highly writable


def test_loci_for_gene_safe_harbour():
    g = cl.loci_for_gene("PPP1R12C", "k562")
    assert not g.empty
    assert g["writability"].max() > 0.7
