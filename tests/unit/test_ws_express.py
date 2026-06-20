"""WS-EXPRESS (v6.5), the comprehensive, literature-cited relative-expression model + its HONEST validation.

The hard gate (pre-registered, no-fabrication): the expanded promoter palette is RICHER but still a PROXY, it
must NOT claim outcome-validation, because an independent promoter study (Damdindorj 2014) disagrees with the
anchor (Qin 2010): promoter strength is context-dependent. These tests lock both the model and that honesty.
"""
from __future__ import annotations

from pen_stack.twin.mechanistic import cassette_expression, promoter_info
from pen_stack.validate.immune_calibration import calibrate_axis


def test_palette_is_comprehensive_and_cited():
    from pen_stack.twin.mechanistic import _palette
    pal = {k: v for k, v in _palette().items() if not k.startswith("_")}
    assert len(pal) >= 25 # constitutive + tissue-specific, many promoters
    # spans constitutive and tissue-specific, each entry carries a context
    for name in ("ef1a", "cmv", "ubc", "sffv", "tbg", "mhck7", "camkiia", "gfaabc1d"):
        assert name in pal and pal[name].get("context")
    # a high-confidence entry carries a citation (literature-grounded, not invented)
    assert promoter_info("ef1a").get("citation")


def test_promoter_context_is_encoded_not_a_universal_scalar():
    # CMV is flagged context-variable/silencing (the whole point: strength is NOT a single universal number)
    cmv = promoter_info("cmv")
    assert "variable" in str(cmv.get("context", "")).lower()
    r = cassette_expression({"promoter": "cmv"}, {"accessibility": 1.0})
    assert "promoter_context_variable_or_silencing" in r["scope_flags"]
    # an unknown promoter abstains to the documented default, never invents a strength
    assert promoter_info("totally_made_up_promoter")["confidence"] == "default"


def test_modifier_profile_is_a_bounded_range_not_a_point_multiplier():
    r = cassette_expression({"promoter": "ef1a", "wpre": True, "intron": True, "codon_optimized": True},
                            {"accessibility": 1.0})
    mp = r["modifier_profile"]
    assert mp["estimated_uplift_range"][0] == 1.0 # honest lower bound: may do nothing for a transgene
    assert 1.0 < mp["estimated_uplift_range"][1] <= 4.0 # bounded, capped uplift
    assert {"wpre", "intron", "codon_optimization"} <= set(mp["applied"])
    assert "transgene" in mp["caveat"].lower() # the context caveat travels with it


def test_expression_proxy_does_NOT_falsely_claim_validation():
    """The no-fabrication invariant: the Qin/Norrman-anchored palette does NOT predict an INDEPENDENT study
    (Damdindorj 2014), promoter strength is context-dependent, so the gate must return weak_proxy, NOT
    outcome_validated. (A circular check vs the anchor would pass; we must not use it.)"""
    proms = ["cmv", "actb", "sv40", "ef1a", "cag", "hsv_tk"]
    proxy = [float(promoter_info(p)["strength"]) for p in proms]
    damdindorj = [1.00, 0.80, 0.65, 0.50, 0.40, 0.20] # independent (10.1371/journal.pone.0106472)
    res = calibrate_axis(proxy, damdindorj, axis="relative_expression")
    assert res["status"] != "outcome_validated" # honest: it does NOT validate cross-study
    assert res["ci"][0] <= 0 # CI includes 0
