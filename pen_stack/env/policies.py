"""Reference policies + rollout for the genome-writing environment (v3.4, WS-ENV).

Two reference policies run end-to-end in `GenomeWritingEnv`:

* ``random_policy`` — uniform over the (fixed) action space, including the reserved abstain action.
* ``greedy_planner_policy`` — the **deterministic optimum**: it reproduces the planner's choices stage by
  stage and always assembles a *rule-legal* plan (a writer/cargo/delivery combination the verifier accepts),
  so it is the reference an RL agent is compared against. **No RL superiority is claimed** — the env is an
  interface + evaluation harness for a near-one-shot decision; ``greedy >= random`` is a sanity check, not a
  result.
"""
from __future__ import annotations

import numpy as np

from pen_stack.env.genome_writing_env import (
    CARGO_BUCKETS,
    WRITE_TYPES,
    WRITER_FAMILIES,
    GenomeWritingEnv,
    demo_candidates,
    writer_form,
)


def random_policy(env: GenomeWritingEnv, obs, rng) -> int:
    return int(rng.integers(0, env.action_space.n))


def _best_delivery_index(env: GenomeWritingEnv, form: str, cargo: int) -> int:
    """Smallest-capacity vehicle compatible with the writer's output form that fits the cargo (a legal,
    efficient choice); falls back to a physical (no-capacity) compatible vehicle."""
    from pen_stack.planner.delivery_vehicles import vehicle
    finite, physical = [], []
    for i, name in enumerate(env.vehicles):
        veh = vehicle(name) or {}
        if form not in veh.get("compatible_cargo_form", []):
            continue
        cap = veh.get("cargo_capacity_bp")
        if cap is None:
            physical.append(i)
        elif cap >= cargo:
            finite.append((cap, i))
    if finite:
        return min(finite)[1]
    if physical:
        return physical[0]
    return 0


def greedy_planner_policy(env: GenomeWritingEnv, obs, rng) -> int:
    """The deterministic optimum at each stage: the supported write type, the best site by base score, its
    highest-activity reachable writer, the smallest cargo bucket that fits, and a form-compatible vehicle."""
    if env._stage == 0:                                        # WRITE TYPE: insertion (fully supported)
        return WRITE_TYPES.index("insertion")
    if env._stage == 1:                                        # SITE: best base score
        scores = [(env.w["safety"] * float(r["safety"]) + env.w["durability"] * float(r["p_durable"]))
                  for _, r in env.cands.iterrows()]
        return int(np.argmax(scores))
    if env._stage == 2:                                        # WRITER: highest-activity reachable (prefer DNA)
        reachable = env.writer_options()
        dna = [f for f in reachable if writer_form(f) == "DNA"] or reachable
        best = max(dna, key=lambda f: env.activity.get(f, 0.0))
        return WRITER_FAMILIES.index(best)
    if env._stage == 3:                                        # CARGO: smallest bucket that fits the target
        fits = [i for i, b in enumerate(CARGO_BUCKETS) if b >= env.cargo_bp] or [len(CARGO_BUCKETS) - 1]
        return fits[0]
    # DELIVERY: smallest-capacity vehicle compatible with the writer's output form
    return _best_delivery_index(env, writer_form(env._writer), env._cargo or env.cargo_bp)


def rollout(env: GenomeWritingEnv, policy, seed: int = 0) -> dict:
    """Run one episode under `policy`; return the cumulative reward + the assembled plan."""
    rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    total, term, info = 0.0, False, {}
    while not term:
        a = policy(env, obs, rng)
        obs, r, term, _trunc, info = env.step(a)
        total += r
    return {"reward": round(total, 4), "plan": env.plan(), "terminal_info": info}


def compare_policies(seed: int = 0) -> dict:
    """Run the random and greedy(planner) policies on the same env — the interface smoke + sanity check. The
    greedy policy is the deterministic optimum and assembles a legal plan; RL is NOT claimed to beat it."""
    rnd = rollout(GenomeWritingEnv(candidates=demo_candidates(n=8, seed=seed), seed=seed),
                  random_policy, seed=seed)
    grd = rollout(GenomeWritingEnv(candidates=demo_candidates(n=8, seed=seed), seed=seed),
                  greedy_planner_policy, seed=seed)
    return {"random": rnd, "greedy_planner": grd,
            "greedy_at_least_random": bool(grd["reward"] >= rnd["reward"]),
            "greedy_plan_legal": bool(grd["plan"]["legal"]),
            "note": "interface only — greedy(planner) is the deterministic optimum; no RL superiority claimed."}
