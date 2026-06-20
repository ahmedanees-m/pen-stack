"""WS-OPT1 / WS-ENV interface tests - Gymnasium env. Skips cleanly if gymnasium is absent."""
from __future__ import annotations

import pytest

gym = pytest.importorskip("gymnasium")

from pen_stack.env.genome_writing_env import ( # noqa: E402
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
        a = 0 # action 0 never the abstain sentinel -> walks all 5 stages
        obs, r, term, trunc, info = env.step(a)
        assert env.observation_space.contains(obs)
        assert isinstance(r, float) and isinstance(term, bool) and isinstance(trunc, bool)
        steps += 1
    assert term and steps == 5 # write_type -> site -> writer -> cargo -> delivery, then terminate


def test_gymnasium_env_checker():
    from gymnasium.utils.env_checker import check_env
    check_env(GenomeWritingEnv(seed=1), skip_render_check=True)


def test_random_and_greedy_policies_run():
    env = GenomeWritingEnv(candidates=demo_candidates(n=8, seed=2), seed=2)
    r_rand = rollout(env, random_policy, seed=2)
    r_grd = rollout(GenomeWritingEnv(candidates=demo_candidates(n=8, seed=2), seed=2),
                    greedy_planner_policy, seed=2)
    assert "reward" in r_rand
    assert r_grd["plan"]["writer"] in WRITER_FAMILIES


def test_greedy_at_least_random_interface_only():
    res = compare_policies(seed=3)
    assert res["greedy_at_least_random"]
    assert "no RL superiority claimed" in res["note"]
