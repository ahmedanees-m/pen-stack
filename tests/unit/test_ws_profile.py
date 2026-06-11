"""WS-PROFILE unit tests (Phase 5.6) - unified per-design immune-risk profile (never collapsed).

CI-safe. Asserts: the profile returns ALL axes, each with its own value + uncertainty + scope + validation
label; the central gate `collapsed_score is None` (no fused number); known-unknowns listed; abstaining axes
report None (not a guess); verify() exposes it; the WS-EXT route modifier + new known-unknowns are present."""
from __future__ import annotations

from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.immune_profile import (
    KNOWN_UNKNOWNS,
    ROUTE_MODIFIER_DOI,
    immune_profile,
)

_AXES = {"genotoxicity", "cd8_epitope", "innate", "preexisting_nab", "anti_peg"}


def test_profile_returns_all_axes_with_uncertainty_and_label():
    p = immune_profile({"delivery_vehicle": "lnp_mrna", "cargo_seq": "AUGGCCUACGG" * 6,
                        "writer_output_form": "mRNA"})
    assert set(p["axes"]) == _AXES
    for axis, rec in p["axes"].items():
        assert set(rec) >= {"value", "uncertainty", "in_scope", "available", "validation", "scope_card"}
        assert "proxy" in rec["validation"].lower()        # WS-CALIB labels travel with the profile


def test_profile_is_never_collapsed_into_one_number():
    # the central WS-PROFILE gate: no single fused score (that would fake confidence).
    p = immune_profile({"delivery_vehicle": "AAV_single"})
    assert p["collapsed_score"] is None
    assert "score" not in {k for k in p if k not in ("collapsed_score",)}  # no top-level fused score field


def test_known_unknowns_listed_and_magnitude_never_predicted():
    p = immune_profile({"delivery_vehicle": "AAV_single"})
    assert "patient_specific_titer" in p["known_unknowns"]
    assert "in_vivo_response_magnitude" in p["known_unknowns"]
    # v5.6 WS-EXT registered the mechanistically-distinct axes as known-unknowns
    assert {"cd4_mhcii_help", "preexisting_capsid_tcell", "complement_carpa"} <= set(KNOWN_UNKNOWNS)
    assert p["no_fabrication"] is True


def test_abstaining_axis_reports_none_not_a_guess():
    # AAV is non-PEGylated -> the anti-PEG axis must abstain (value None), not fabricate a number.
    p = immune_profile({"delivery_vehicle": "AAV_single"})
    assert p["axes"]["anti_peg"]["value"] is None and p["axes"]["anti_peg"]["available"] is False
    # for a PEGylated LNP it is present
    lnp = immune_profile({"delivery_vehicle": "lnp_mrna"})
    assert lnp["axes"]["anti_peg"]["value"] is not None


def test_route_modifier_is_documented_not_fabricated():
    priv = immune_profile({"delivery_vehicle": "AAV_single", "route": "subretinal"})["route_modifier"]
    assert priv["immune_privileged"] is True and priv["doi"] == ROUTE_MODIFIER_DOI
    assert citations_grounded([ROUTE_MODIFIER_DOI])["all_grounded"] is True
    syst = immune_profile({"delivery_vehicle": "AAV_single", "route": "intravenous"})["route_modifier"]
    assert syst["immune_privileged"] is False
    assert immune_profile({"delivery_vehicle": "AAV_single"})["route_modifier"] is None


def test_verify_exposes_the_immune_profile():
    from pen_stack.verify import verify
    v = verify({"write_type": "insertion", "writer_family": "bridge_IS110", "writer_output_form": "mRNA",
                "cargo_bp": 2000, "delivery_vehicle": "lnp_mrna", "cargo_seq": "AUGGCCUAC" * 6})
    assert v.immune_profile is not None
    assert v.immune_profile["collapsed_score"] is None
    assert set(v.immune_profile["axes"]) == _AXES
    assert v.no_fabrication is True
