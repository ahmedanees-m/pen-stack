"""WS-GEN / WS-PARETO / WS-ORCH unit tests (Phase 5.8, the generative designer).

CI-safe: the discriminator + Pareto + orchestrator logic is exercised on EXPLICIT candidate fixtures (no atlas
needed; the planner-backed candidate_space is the data/VM path). Audit writes go to a tmp file. Asserts:
  * verifier-as-discriminator: hazardous (safety refuse) AND illegal candidates are DISCARDED, never returned;
  * survivors are legal + safe, each output_kind="candidate" with a calibrated confidence + a v5.6 immune profile;
  * Pareto frontier is non-dominated and the neg_immune_risk axis is GROUNDED by the v5.6 profile (uncertainty
    band carried, in-vivo magnitude scope-flagged), never a placeholder;
  * live orchestration is replayable (seed-locked, identical trace) and fabricates no number.
"""
from __future__ import annotations

import pytest

from pen_stack.design.generate import generate_designs
from pen_stack.design.pareto import AXES, neg_immune_risk, pareto_front

_BENIGN_AAV = {"write_type": "insertion", "gene": "AAVS1", "chrom": "chr19",
               "edit_intent": "safe_harbour_insertion", "writer_family": "bridge_IS110", "cargo_bp": 3000,
               "cell_type": "k562", "delivery_vehicle": "AAV_single",
               "safety": 0.92, "p_durable": 0.80, "writer_activity": 0.70, "deliverability": 0.36}
_BENIGN_DUAL = {**_BENIGN_AAV, "delivery_vehicle": "AAV_dual", "writer_activity": 0.55, "deliverability": 0.66}
_HAZARD = {**_BENIGN_AAV, "cargo_function": "ricin-like RIP", "pfam_domains": ["PF00161"]}
_ILLEGAL_OVERSIZE = {**_BENIGN_AAV, "cargo_bp": 8000, "delivery_vehicle": "AAV_single"}
_ILLEGAL_FORM = {**_BENIGN_AAV, "delivery_vehicle": "lnp_mrna"} # dsDNA writer can't ship as mRNA


@pytest.fixture(autouse=True)
def _hermetic_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("PEN_STACK_SAFETY_AUDIT", str(tmp_path / "audit.log"))


def _survivors():
    return generate_designs(
        candidates=[_BENIGN_AAV, _BENIGN_DUAL, _HAZARD, _ILLEGAL_OVERSIZE, _ILLEGAL_FORM], keep=10)


# --- WS-GEN: verifier-as-discriminator ------------------------------------------------

def test_hazardous_and_illegal_never_survive():
    surv = _survivors()
    vehicles = {s["delivery_vehicle"] for s in surv}
    assert vehicles == {"AAV_single", "AAV_dual"}, vehicles # only the legal+safe benign pair
    # hazard (ricin) and the two illegal designs are gone
    assert all(s.get("cargo_function") != "ricin-like RIP" for s in surv)
    assert all(s["cargo_bp"] <= 4700 for s in surv if s["delivery_vehicle"] == "AAV_single")


def test_survivors_are_candidates_with_confidence_and_immune_profile():
    for s in _survivors():
        assert s["output_kind"] == "candidate" # never asserted to work
        assert s["legal"] is True and s["safety_decision"] in ("clear", "flag")
        assert s["confidence"] is not None # calibrated (scores supplied)
        assert s["immune_profile"] is not None and "axes" in s["immune_profile"]
        assert s["immune_profile"]["collapsed_score"] is None # v5.6 invariant preserved


def test_empty_pool_returns_empty():
    assert generate_designs(candidates=[]) == []


def test_deliverability_and_compatibility_grounded():
    from pen_stack.design.space import _compatible_vehicles, deliverability_score
    assert 0.0 < deliverability_score("AAV_single", 3000) < 1.0 # fits with headroom
    assert deliverability_score("AAV_single", 6000) == 0.0 # over the 4700 bp capacity
    assert deliverability_score("electroporation", 99999) == 1.0 # no packaging limit
    compat = _compatible_vehicles(3000)
    assert "AAV_single" in compat and "AAV_dual" in compat
    assert "AAV_single" not in _compatible_vehicles(6000) # excluded over capacity


def test_candidate_space_graceful_without_atlas():
    from pen_stack.design.space import candidate_space
    # with the Phase-1 atlas absent (CI), plan_write yields nothing -> [] (never crashes)
    out = candidate_space({"gene": "AAVS1", "intent": "safe_harbour_insertion", "cargo_bp": 3000})
    assert isinstance(out, list)


# --- WS-PARETO: grounded immune-risk axis + non-dominance ------------------------------

def test_pareto_front_is_non_dominated():
    front = pareto_front(_survivors())
    assert front
    from pen_stack.design.pareto import _dominates
    for f in front:
        assert not any(_dominates(o, f) for o in front if o is not f)
        assert set(f["scores"]) == set(AXES)


def test_neg_immune_risk_is_grounded_not_placeholder():
    s = _survivors()[0]
    detail = neg_immune_risk(s)
    # value equals the worst-case in-scope axis value from the v5.6 profile (sourced, not constant)
    axes = s["immune_profile"]["axes"]
    in_scope = [a["value"] for a in axes.values() if a["in_scope"] and a["value"] is not None]
    assert detail["value"] == pytest.approx(min(in_scope))
    assert detail["scope_flag"] == "in_vivo_magnitude_unknown" # in-vivo magnitude stays flagged
    assert detail["uncertainty"] >= 0.0 and detail["axes_used"]


def test_dominated_design_excluded_from_front():
    surv = _survivors()
    best = surv[0]
    worse = {**best, "writer_activity": 0.01, "p_durable": 0.01, "safety": 0.01, "deliverability": 0.01,
             "cargo_bp": 9999}
    front = pareto_front([best, worse])
    # the strictly-worse design (same immune profile, lower on every other axis) is dominated -> excluded
    assert len(front) == 1
    assert front[0]["writer_activity"] == best["writer_activity"]


# --- WS-ORCH: replayable, no fabrication -----------------------------------------------

def test_orchestrate_replayable_and_no_fabrication():
    from pen_stack.agent.orchestrator_live import orchestrate
    goal = {"gene": "AAVS1", "intent": "safe_harbour_insertion", "cargo_bp": 3000, "cell_type": "k562"}
    pool = [_BENIGN_AAV, _BENIGN_DUAL, _HAZARD]
    r1 = orchestrate(goal, candidates=pool, seed=0)
    r2 = orchestrate(goal, candidates=pool, seed=0)
    assert r1["no_fabrication"] is True
    assert r1["design"] is not None and r1["design"]["output_kind"] == "candidate"
    # seed-locked replay reproduces the trace (deterministic; numbers tool-sourced)
    assert [t["verdict"] for t in r1["trace"]] == [t["verdict"] for t in r2["trace"]]
    assert all(t.get("safety") in ("clear", "flag", None) for t in r1["trace"])
