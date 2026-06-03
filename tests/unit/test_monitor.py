"""Phase 2, Step 2.7 - PEN-MONITOR living-database engine.

Offline: triage classifies a synthetic ISPpu10 hit to bridge_IS110, carries a citation, and marks it
pending_review (never auto-accepted). Network (optional): the back-test surfaces ISPpu10 (PPR1218813).
"""
from __future__ import annotations

import pytest

from pen_stack.monitor.run import run_monitor
from pen_stack.monitor.triage import triage_hit

_ISPPU10_HIT = {
    "id": "PPR1218813", "source": "PPR", "doi": "10.64898/2026.03.19.712850",
    "title": "ISPpu10 is a structure-gated bridge RNA recombinase",
    "abstractText": "An IS110 bridge recombinase from Pseudomonas putida drives genomic plasticity.",
    "firstPublicationDate": "2026-03-20",
}


def test_triage_classifies_and_cites():
    row = triage_hit(_ISPPU10_HIT)
    assert row["candidate_family"] == "bridge_IS110"
    assert row["source_id"] == "PPR1218813"
    assert row["doi"]                       # carries a citation
    assert row["status"] == "pending_review"   # never auto-accepted into the atlas


def test_triage_never_autoedits():
    # the triage row is a *candidate* only - confidence inferred, status pending
    row = triage_hit(_ISPPU10_HIT)
    assert row["confidence"] == "inferred"
    assert row["status"] != "accepted"


def _has_network() -> bool:
    try:
        from pen_stack.monitor.europepmc import search
        search("ISPpu10", since_date="2026-01-01", page_size=1, timeout=8)
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _has_network(), reason="Europe PMC not reachable")
def test_backtest_surfaces_isppu10(tmp_path):
    res = run_monitor(since="2026-01-01", back_test=True, out=tmp_path / "q.csv")
    assert res["isppu10_found"] is True
    assert res["n_candidates"] > 0
