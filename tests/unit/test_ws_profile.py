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

_AXES = {"genotoxicity", "cd8_epitope", "innate", "preexisting_nab", "anti_peg",
         "mhc2_writer", "ada_writer"} # v6.9, CD4/MHC-II + ADA over the writer enzyme


def test_profile_returns_all_axes_with_uncertainty_and_label():
    p = immune_profile({"delivery_vehicle": "lnp_mrna", "cargo_seq": "AUGGCCUACGG" * 6,
                        "writer_output_form": "mRNA"})
    assert set(p["axes"]) == _AXES
    for axis, rec in p["axes"].items():
        assert set(rec) >= {"value", "uncertainty", "in_scope", "available", "validation", "scope_card"}
        assert "proxy" in rec["validation"].lower() # WS-CALIB labels travel with the profile


def test_innate_axis_derives_cargo_form_from_vehicle():
    # v7.1.6: when a cargo sequence is supplied but no explicit cargo_form, the form is derived from the vehicle's
    # defining cargo class (DNA vehicle -> CpG/TLR9), so the innate axis computes for any caller. No fabrication:
    # still abstains with no sequence, and an explicit form always wins.
    from pen_stack.planner.immune_profile import _vehicle_cargo_form
    assert _vehicle_cargo_form("AAV_single") == "DNA"
    assert _vehicle_cargo_form("lnp_mrna") == "mRNA"
    assert _vehicle_cargo_form("evlp") == "RNP"
    assert _vehicle_cargo_form("totally_unknown_vehicle") is None
    # DNA vehicle + cargo_seq, no explicit cargo_form -> innate now computes (was abstaining before v7.1.6).
    dna = immune_profile({"delivery_vehicle": "AAV_single", "cargo_seq": "ACGTACGTACGTCGCGCGCGATATAT"})
    assert dna["axes"]["innate"]["available"] is True and dna["axes"]["innate"]["value"] is not None
    # no cargo sequence -> still abstains (never a guessed value).
    none = immune_profile({"delivery_vehicle": "AAV_single"})
    assert none["axes"]["innate"]["available"] is False and none["axes"]["innate"]["value"] is None
    # an explicit cargo_form overrides the vehicle-derived default.
    forced = immune_profile({"delivery_vehicle": "AAV_single", "cargo_seq": "ACGUACGUACGU" * 3,
                             "cargo_form": "mRNA"})
    assert forced["axes"]["innate"]["available"] is True


def test_writer_axes_compute_when_a_writer_is_supplied():
    # v7.1.6: the MHC-II/CD4 + ADA writer-as-antigen axes compute when a grounded writer family is named (bundled
    # sequence + committed NetMHCIIpan-4.0 cache), and abstain otherwise. The web form now exposes this input.
    p = immune_profile({"delivery_vehicle": "AAV_single", "writer_family": "serine_integrase"})
    assert p["axes"]["mhc2_writer"]["value"] is not None and p["axes"]["mhc2_writer"]["available"] is True
    assert p["axes"]["ada_writer"]["value"] is not None
    assert p["writer_as_antigen"] is not None and p["writer_as_antigen"]["representative"] == "Bxb1"
    # no writer -> the two writer axes abstain (None), never fabricated.
    nw = immune_profile({"delivery_vehicle": "AAV_single"})
    assert nw["axes"]["mhc2_writer"]["value"] is None and nw["axes"]["ada_writer"]["value"] is None


def test_writer_immunogenicity_table_for_the_writer_atlas():
    # v7.1.8: the writer-as-antigen immunogenicity (MHC-II + ADA) is surfaced on the Writer Atlas, read from the
    # committed NetMHCIIpan-4.0 cache (no recompute). It covers the genome-writer families (serine integrase Bxb1,
    # bridge ISCro4) and EXCLUDES the Cas9 nuclease (an editor, not a large-cargo writer) and the human self control.
    from pen_stack.planner.immune_profile import writer_immunogenicity_table
    t = writer_immunogenicity_table()
    reps = {w["representative"] for w in t}
    fams = {w["writer_family"] for w in t}
    assert {"Bxb1", "ISCro4"} <= reps
    assert "SpCas9" not in reps and "HumanAlbumin" not in reps  # Cas9 removed; self control excluded
    assert fams == {"serine_integrase", "bridge_IS110"}
    for w in t:
        assert w["mhc2_immune_score"] is not None and w["ada_immune_score"] is not None  # grounded, from the cache
        assert w["is_foreign"] is True


def test_administration_context_mutes_vector_facing_axes_ex_vivo():
    # v7.1.7: ex-vivo administration (cells transduced in a dish, washed before transplant) bypasses the patient's
    # circulating antibodies, so the pre-existing anti-vector NAb axis is muted to "no barrier" (1.0) and the
    # capsid CD8 axis is flagged muted (intrinsic value kept). In-vivo / unspecified leave the axes untouched.
    inv = immune_profile({"delivery_vehicle": "AAV_single", "in_vivo": True})
    exv = immune_profile({"delivery_vehicle": "AAV_single", "in_vivo": False})
    none = immune_profile({"delivery_vehicle": "AAV_single"})
    # modifier block reflects the context (or is absent when unspecified)
    assert inv["administration_modifier"]["context"] == "in_vivo"
    assert exv["administration_modifier"]["context"] == "ex_vivo"
    assert none["administration_modifier"] is None
    # in-vivo and unspecified keep the grounded seroprevalence value; ex-vivo mutes it to no-barrier 1.0
    nab_in = inv["axes"]["preexisting_nab"]["value"]
    assert nab_in == none["axes"]["preexisting_nab"]["value"] and nab_in is not None and nab_in < 1.0
    nab_ex = exv["axes"]["preexisting_nab"]
    assert nab_ex["value"] == 1.0 and nab_ex["administration_muted"] is True
    assert nab_ex["pre_admin_value"] == nab_in  # the original value is preserved, not discarded
    # CD8 capsid is flagged muted ex-vivo but its intrinsic value is unchanged (transduced cells still present)
    assert exv["axes"]["cd8_epitope"]["administration_muted"] is True
    assert exv["axes"]["cd8_epitope"]["value"] == inv["axes"]["cd8_epitope"]["value"]
    # no fabrication: genotoxicity (an intrinsic integration property) is NOT muted by administration context
    assert exv["axes"]["genotoxicity"]["value"] == inv["axes"]["genotoxicity"]["value"]


def test_profile_is_never_collapsed_into_one_number():
    # the central WS-PROFILE gate: no single fused score (that would fake confidence).
    p = immune_profile({"delivery_vehicle": "AAV_single"})
    assert p["collapsed_score"] is None
    assert "score" not in {k for k in p if k not in ("collapsed_score",)} # no top-level fused score field


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
