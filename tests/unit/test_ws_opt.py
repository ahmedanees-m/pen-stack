"""WS-OPT1 unit tests (Phase 3.2) - Gymnasium env interface. Skips cleanly if gymnasium is absent."""
from __future__ import annotations

import pytest

gym = pytest.importorskip("gymnasium")

from pen_stack.env.genome_writing_env import (  # noqa: E402
    WRITER_FAMILIES,
    GenomeWritingEnv,
    compare_policies,
    demo_candidates,
    greedy_planner_policy,
    random_policy,
    rollout,
)


def test_env_conforms_to_gymnasium_api():
    env = GenomeWritingEnv(seed=0)
    obs, info = env.reset(seed=0)
    assert env.observation_space.contains(obs)
    assert isinstance(info, dict)
    term = False
    steps = 0
    while not term and steps < 10:
        a = env.action_space.sample()
        obs, r, term, trunc, info = env.step(a)
        assert env.observation_space.contains(obs)
        assert isinstance(r, float) and isinstance(term, bool) and isinstance(trunc, bool)
        steps += 1
    assert term and steps == 3            # site -> writer -> cargo, then terminate


def test_gymnasium_env_checker():
    from gymnasium.utils.env_checker import check_env
    # the official checker validates spaces/reset/step contracts
    check_env(GenomeWritingEnv(seed=1), skip_render_check=True)


def test_random_and_greedy_policies_run():
    env = GenomeWritingEnv(candidates=demo_candidates(n=8, seed=2), seed=2)
    r_rand = rollout(env, random_policy, seed=2)
    r_grd = rollout(GenomeWritingEnv(candidates=demo_candidates(n=8, seed=2), seed=2),
                    greedy_planner_policy, seed=2)
    assert "reward" in r_rand and r_rand["plan"]["site"] is not None
    assert r_grd["plan"]["writer"] in WRITER_FAMILIES


def test_greedy_at_least_random_interface_only():
    # the greedy(planner) policy is the deterministic optimum; it should not underperform random
    res = compare_policies(seed=3)
    assert res["greedy_at_least_random"]
    assert "no RL superiority claimed" in res["note"]
