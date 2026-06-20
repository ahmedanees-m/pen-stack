"""WS-ENV unit tests (Phase 3.4) - the full genome-writing environment over the router + verifier.

Asserts the pre-registered MDP (prereg/ws_env.yaml): verifier-driven step validity, the legal/illegal/refusal
reward contract, the abstain action, and the greedy>=random + greedy-legal sanity over the frozen seed set.
Skips cleanly if gymnasium is absent (the [env] extra).
"""
from __future__ import annotations

import pytest

gym = pytest.importorskip("gymnasium")

from pen_stack.env.genome_writing_env import ( # noqa: E402
    CARGO_BUCKETS,
    WRITE_TYPES,
    WRITER_FAMILIES,
    GenomeWritingEnv,
    compare_policies,
    writer_form,
)
from pen_stack.env.policies import greedy_planner_policy, rollout # noqa: E402


def _drive(env, write_type, site, writer, cargo, delivery):
    """Walk the env through explicit choices (indices), return the terminal info dict."""
    env.reset(seed=0)
    env.step(WRITE_TYPES.index(write_type))
    env.step(site)
    env.step(WRITER_FAMILIES.index(writer))
    env.step(CARGO_BUCKETS.index(cargo))
    _o, r, term, _t, info = env.step(env.vehicles.index(delivery))
    assert term
    return r, info


def test_writer_form_map():
    assert writer_form("bridge_IS110") == "DNA"
    assert writer_form("Cas9") == "RNP" and writer_form("Cas12a") == "RNP"


def test_legal_plan_rewarded_with_calibrated_confidence():
    env = GenomeWritingEnv(seed=0)
    r, info = _drive(env, "insertion", 0, "bridge_IS110", 3000, "AAV_single")
    assert info["legal"] is True and not info["deferred"]
    assert info["confidence"] is not None # the verifier attached a calibrated confidence
    assert r > 0.0


def test_illegal_plan_penalised_rnp_into_aav():
    # Cas9 delivers RNP; AAV carries DNA -> verifier rejects (delivery.cargo_form_compatible) -> penalty
    env = GenomeWritingEnv(seed=0)
    r, info = _drive(env, "insertion", 0, "Cas9", 1000, "AAV_single")
    assert info["legal"] is False
    assert "delivery.cargo_form_compatible" in info["violations"]
    assert r == pytest.approx(-1.0)


def test_illegal_oversize_cargo_penalised():
    # 30 kb cargo into single AAV (cap 4700) -> payload.cargo_within_capacity violated
    env = GenomeWritingEnv(seed=0)
    r, info = _drive(env, "insertion", 0, "bridge_IS110", 30000, "AAV_single")
    assert info["legal"] is False
    assert "payload.cargo_within_capacity" in info["violations"]
    assert r == pytest.approx(-1.0)


def test_abstain_action_ends_episode_with_refusal():
    env = GenomeWritingEnv(seed=0)
    env.reset(seed=0)
    obs, r, term, trunc, info = env.step(env.action_space.n - 1) # reserved abstain action
    assert term and info["abstained"] is True
    assert r > -1.0 and r < 0.5 # beats illegal, loses to a good legal plan


def test_greedy_beats_random_and_is_legal_on_frozen_seeds():
    for seed in range(8): # frozen seed set in the prereg
        res = compare_policies(seed=seed)
        assert res["greedy_at_least_random"], f"seed {seed}: greedy < random"
        assert res["greedy_plan_legal"], f"seed {seed}: greedy plan illegal"


def test_greedy_assembles_a_complete_legal_plan():
    grd = rollout(GenomeWritingEnv(seed=5), greedy_planner_policy, seed=5)
    p = grd["plan"]
    assert p["legal"] is True and p["refused"] is False
    assert p["write_type"] == "insertion" and p["delivery"] is not None
