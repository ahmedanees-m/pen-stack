"""WS-WV unit tests (Phase 4.0) - writer-verification: score/critique, never invent. CI-safe (frozen panel
when the Perry DMS is absent; structure oracle deferred without a backend)."""
from __future__ import annotations

from pen_stack.atlas import writer_verify as WV


def test_blind_recovery_recovers_known_enhancers_above_worse():
    r = WV.blind_recovery()
    assert r["available"] and r["all_enhancers_recovered"] is True
    assert r["enhancers_outrank_worse"] is True
    for e in ("N322P", "H50K", "R278M"):
        assert r["recovered"][e] is True


def test_measured_variant_is_claimable_unmeasured_is_not():
    scores = {s.variant: s for s in WV.score_variants(["N322P", "ZZZ999A"])}
    assert scores["N322P"].claimable is True and scores["N322P"].in_dms is True
    assert scores["N322P"].score is not None and scores["N322P"].interval is not None
    # a variant with no measured/in-distribution support: flagged, NOT claimable, NO activity asserted
    assert scores["ZZZ999A"].claimable is False and scores["ZZZ999A"].extrapolating is True
    assert scores["ZZZ999A"].score is None


def test_critique_flags_a_bad_candidate_and_never_claims_it_works():
    c = WV.critique_candidate("M" + "A" * 330, writer_family="bridge_IS110",
                              site_seq="ACGT", delivery_vehicle="AAV_single")
    assert c["pass"] is False
    assert c["no_claim"] is True and c["claimable"] is False     # WV2 never asserts a generated writer works
    assert "active_site_implausible" in c["flags"] or "fold_unverified" in c["flags"]


def test_critique_fold_unverified_without_structure_backend():
    c = WV.critique_candidate("MKT" * 110)
    # no AF3/Boltz/Chai/Protenix backend in CI -> fold is unverified, not assumed
    assert c["fold_ok"] is False and "fold_unverified" in c["flags"]
    assert c["claimable"] is False


def test_verifier_attaches_writer_critique_as_scope_not_confidence():
    from pen_stack.verify import verify
    v = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=3000,
                    delivery_vehicle="AAV_single", writer_candidate_seq="M" + "A" * 330))
    assert v.writer_critique is not None
    assert v.writer_critique["no_claim"] is True and v.writer_critique["claimable"] is False
    assert any(s.get("kind") == "writer_candidate_critique" for s in v.scope_flags)
    assert v.no_fabrication is True
    # control: no candidate -> no critique
    v2 = verify(dict(write_type="insertion", writer_family="bridge_IS110", cargo_bp=3000,
                     delivery_vehicle="AAV_single"))
    assert v2.writer_critique is None
