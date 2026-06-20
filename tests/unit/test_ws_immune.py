"""WS-IMMUNE unit tests (Phase 5.1) - delivery safety<->efficacy balance over DOCUMENTED immune priors.

CI-safe (pure config + arithmetic; no network, no heavy data). Asserts: every vehicle carries a complete
documented immune_safety block with curated+grounded DOIs; the two safety sub-axes are reproduced from the
tiers; the user's stated tradeoff (AAV dinged on immunogenicity, lentivirus on genotoxicity) holds; the
ranking moves with safety_weight; capacity/route filters work; verify() surfaces the profile WITHOUT
predicting a magnitude (the in-vivo immune magnitude stays a known-unknown)."""
from __future__ import annotations

from pen_stack.agent.cite import citations_grounded
from pen_stack.planner.delivery_immunology import (
    recommend_delivery,
    safety_efficacy_profile,
)
from pen_stack.planner.delivery_vehicles import names

_IMMUNE_AXES = ("preexisting_immunity", "neutralizing_antibody", "innate_immune", "adaptive_immune")


def test_all_vehicles_have_documented_immune_block_with_grounded_dois():
    for n in names():
        p = safety_efficacy_profile(n)
        assert p is not None, n
        # complete ordinal tiers
        for ax in (*_IMMUNE_AXES, "genotoxicity", "efficacy"):
            assert p["tiers"][ax] is not None, f"{n} missing tier {ax}"
        # a documented tradeoff sentence and >=1 curated, grounded immune DOI
        assert p["tradeoff"], n
        assert p["immune_dois"], n
        assert citations_grounded(p["immune_dois"])["all_grounded"] is True, n
        # every score is a normalised function of the tiers, in [0, 1]
        for k in ("immune_score", "genotox_score", "safety_score", "efficacy_score"):
            assert p[k] is None or 0.0 <= p[k] <= 1.0, (n, k, p[k])
        # headline safety is the worst (min) of the two safety sub-axes
        assert p["safety_score"] == min(p["immune_score"], p["genotox_score"])


def test_users_stated_tradeoff_is_reproduced():
    """AAV: safe by integration but immunogenicity-limited; lentivirus: efficacious integrator but genotoxic."""
    aav = safety_efficacy_profile("AAV_single")
    lv = safety_efficacy_profile("lentivirus")
    # AAV headline safety is driven by IMMUNOGENICITY (immune worse than genotox); it is non-integrating.
    assert aav["immune_score"] < aav["genotox_score"]
    assert aav["integrating"] is False
    # lentivirus headline safety is driven by GENOTOXICITY (genotox worse than immune); it is highly efficacious.
    assert lv["genotox_score"] < lv["immune_score"]
    assert lv["integrating"] is True
    assert lv["efficacy_score"] == 1.0


def test_ranking_moves_with_safety_weight():
    # safety-first vs efficacy-first produce different orderings of the same eligible DNA palette.
    safe = recommend_delivery("DNA", cargo_bp=4000, safety_weight=1.0)
    effi = recommend_delivery("DNA", cargo_bp=4000, safety_weight=0.0)
    assert safe["recommended"] is not None and effi["recommended"] is not None
    safe_order = [p["vehicle"] for p in safe["ranked"]]
    effi_order = [p["vehicle"] for p in effi["ranked"]]
    assert safe_order != effi_order
    # under pure-safety weighting the top vehicle's balance equals its safety_score
    top = safe["ranked"][0]
    assert top["balance"] == top["safety_score"]
    # HDAd (strong anti-Ad immunity) ranks strictly below AAV under safety-first
    assert safe_order.index("helper_dependent_adenovirus") > safe_order.index("AAV_single")


def test_capacity_and_form_filters_exclude_incompatible_vehicles():
    # an oversize DNA cargo (12 kb) excludes single/dual AAV (capacity exceeded) but keeps HDAd/HSV.
    r = recommend_delivery("DNA", cargo_bp=12000, safety_weight=0.5)
    eligible = {p["vehicle"] for p in r["ranked"]}
    excluded = {e["vehicle"] for e in r["excluded"]}
    assert "AAV_single" in excluded and "AAV_dual" in excluded
    assert "helper_dependent_adenovirus" in eligible and "hsv_amplicon" in eligible
    # an RNP cargo only keeps RNP-compatible vehicles (lnp_mrna / evlp / electroporation)
    rnp = {p["vehicle"] for p in recommend_delivery("RNP")["ranked"]}
    assert rnp <= {"lnp_mrna", "evlp", "electroporation"}
    assert "AAV_single" not in rnp and "lentivirus" not in rnp


def test_magnitude_stays_a_known_unknown_never_predicted():
    # every profile carries the standing scope flag pointing at the in_vivo_immunogenicity known-unknown
    p = safety_efficacy_profile("AAV_single")
    assert p["magnitude_scope_flag"]["id"] == "in_vivo_immunogenicity"
    # recommend_delivery carries the same scope flag and asserts no fabrication
    r = recommend_delivery("DNA", cargo_bp=3000)
    assert any(f["id"] == "in_vivo_immunogenicity" for f in r["scope_flags"])
    assert r["no_fabrication"] is True


def test_verify_surfaces_delivery_profile_without_confidence_from_immune_priors():
    from pen_stack.verify import verify
    v = verify({"write_type": "insertion", "writer_family": "bridge_IS110", "cargo_bp": 3000,
                "delivery_vehicle": "lentivirus"})
    assert v.delivery_profile is not None
    assert v.delivery_profile["vehicle"] == "lentivirus"
    # the documented immune tradeoff is surfaced as a scope flag, and the magnitude stays out of scope
    immune_flag = [f for f in v.scope_flags if f.get("kind") == "delivery_immune_profile"]
    assert immune_flag and immune_flag[0]["magnitude_id"] == "in_vivo_immunogenicity"
    # the immune priors NEVER produce confidence (a vehicle with no per-axis scores must abstain)
    assert v.confidence is None
    assert v.no_fabrication is True
