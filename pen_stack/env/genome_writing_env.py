"""Gymnasium environment INTERFACE for genome-write planning (Phase 3.2, WS-OPT1).

A thin `gymnasium.Env` wrapper over the deterministic planner so agent-developer tooling (RL libraries, env
suites) can drive PEN-STACK through a standard interface. An episode builds a write plan as a short sequence
of decisions:

    stage 0: choose a SITE (a candidate bin) -> stage 1: choose a WRITER family ->
    stage 2: choose a CARGO size bucket -> terminate; reward = the plan's validity/score.

Reward reuses the planner's transparent components (safety, durability, writer activity, intent weights from
`configs/intent_weights.yaml`) with penalties for an unreachable writer or a cargo that no reachable writer
can deliver — i.e. the same objective the deterministic planner optimises.

**Explicitly an INTERFACE, not a claim.** The genome-writing decision is near-one-shot, so RL benefit is
unproven; no RL agent is claimed to beat the deterministic planner. The greedy(planner) policy here *is* the
deterministic optimum and is provided as the reference. Behind the optional `[env]` extra (gymnasium); the
rest of PEN-STACK does not import this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import gymnasium as gym
    from gymnasium import spaces
    _HAVE_GYM = True
except Exception:  # noqa: BLE001 - gymnasium only in the [env] extra
    _HAVE_GYM = False
    gym = None
    spaces = None

from pen_stack.planner.optimize import (
    EditIntent,
    load_intent_weights,
    writer_activity_by_family,
)

WRITER_FAMILIES = ["bridge_IS110", "seek_IS1111", "CAST_VK", "serine_integrase",
                   "PE_integrase", "Cas9", "Cas12a"]
CARGO_BUCKETS = [1000, 3000, 6000, 12000, 30000]   # bp
_N_STAGES = 3


def demo_candidates(n: int = 8, seed: int = 0) -> pd.DataFrame:
    """A small synthetic candidate table (safety, p_durable, reachable_tier1) so the env runs without the
    Phase-1 atlas. Real use passes the Phase-1 writability atlas rows instead."""
    rng = np.random.default_rng(seed)
    fams = [";".join(rng.choice(WRITER_FAMILIES, size=rng.integers(2, 5), replace=False)) for _ in range(n)]
    return pd.DataFrame({"chrom": ["chr1"] * n, "bin": list(range(n)),
                         "safety": rng.uniform(0.3, 0.95, n).round(3),
                         "p_durable": rng.uniform(0.3, 0.95, n).round(3),
                         "reachable_tier1": fams})


def _base():
    return gym.Env if _HAVE_GYM else object


class GenomeWritingEnv(_base()):
    """Gymnasium interface over the planner (see module docstring). Conforms to reset/step/spaces."""
    metadata = {"render_modes": []}

    def __init__(self, candidates: pd.DataFrame | None = None,
                 intent: str | EditIntent = "safe_harbour_insertion", cargo_bp: int = 3000, seed: int = 0):
        if not _HAVE_GYM:
            raise ImportError("GenomeWritingEnv needs the optional [env] extra: pip install pen-stack[env]")
        super().__init__()
        self.cands = (candidates if candidates is not None else demo_candidates(seed=seed)).reset_index(drop=True)
        self.intent = EditIntent(intent) if not isinstance(intent, EditIntent) else intent
        self.cargo_bp = int(cargo_bp)
        self.w = load_intent_weights()["intents"][self.intent.value]
        self.activity = writer_activity_by_family()
        self.n_sites = len(self.cands)
        # fixed Discrete action space sized to the largest stage; actions are taken modulo the stage's options
        self.action_space = spaces.Discrete(max(self.n_sites, len(WRITER_FAMILIES), len(CARGO_BUCKETS)))
        # observation: [stage/Nstages, site_safety, site_p_durable, writer_activity, cargo_frac]
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(5,), dtype=np.float32)
        self._rng = np.random.default_rng(seed)
        self.reset(seed=seed)

    # ---- helpers -------------------------------------------------------------------------------
    def _obs(self) -> np.ndarray:
        site = self.cands.iloc[self._site] if self._site is not None else None
        return np.array([
            self._stage / _N_STAGES,
            float(site["safety"]) if site is not None else 0.0,
            float(site["p_durable"]) if site is not None else 0.0,
            float(self.activity.get(self._writer, 0.0)) if self._writer else 0.0,
            (self._cargo / max(CARGO_BUCKETS)) if self._cargo else 0.0,
        ], dtype=np.float32)

    def site_options(self) -> list[int]:
        return list(range(self.n_sites))

    def writer_options(self) -> list[str]:
        if self._site is None:
            return WRITER_FAMILIES
        return [f for f in str(self.cands.iloc[self._site]["reachable_tier1"]).split(";") if f] or WRITER_FAMILIES

    # ---- Gymnasium API -------------------------------------------------------------------------
    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)              # seeds gymnasium's self.np_random (env-checker contract)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._stage = 0
        self._site = None
        self._writer = None
        self._cargo = None
        return self._obs(), {"stage": "site"}

    def step(self, action: int):
        action = int(action)
        reward, terminated, info = 0.0, False, {}
        if self._stage == 0:                                   # choose SITE
            self._site = self.site_options()[action % self.n_sites]
            info = {"stage": "writer", "chose_site": int(self._site)}
        elif self._stage == 1:                                 # choose WRITER family
            opts = WRITER_FAMILIES
            self._writer = opts[action % len(opts)]
            info = {"stage": "cargo", "chose_writer": self._writer,
                    "writer_reachable": self._writer in self.writer_options()}
        elif self._stage == 2:                                 # choose CARGO bucket -> terminate
            self._cargo = CARGO_BUCKETS[action % len(CARGO_BUCKETS)]
            reward = self._plan_reward()
            terminated = True
            info = {"stage": "done", "chose_cargo_bp": self._cargo, **self.plan()}
        self._stage += 1
        return self._obs(), float(reward), bool(terminated), False, info

    # ---- reward = the planner's transparent objective ------------------------------------------
    def _plan_reward(self) -> float:
        site = self.cands.iloc[self._site]
        reachable = self._writer in self.writer_options()
        act = float(self.activity.get(self._writer, 0.4))
        base = (self.w["safety"] * float(site["safety"])
                + self.w["durability"] * float(site["p_durable"])
                + self.w["activity"] * act)
        if not reachable:                                      # writer cannot engage this site (MC1 spirit)
            base -= 0.5
        if self._cargo < self.cargo_bp:                        # cargo bucket too small for the target insert
            base -= 0.25
        return float(base)

    def plan(self) -> dict:
        return {"site": None if self._site is None else int(self._site),
                "writer": self._writer, "cargo_bp": self._cargo, "intent": self.intent.value}


# --------------------------------------------------------------------------------------------------
# reference policies + rollout (a random policy and the greedy planner policy both run)
# --------------------------------------------------------------------------------------------------
def random_policy(env: "GenomeWritingEnv", obs, rng) -> int:
    return int(rng.integers(0, env.action_space.n))


def greedy_planner_policy(env: "GenomeWritingEnv", obs, rng) -> int:
    """The deterministic optimum at each stage: best site by base score, its highest-activity reachable
    writer, then the smallest cargo bucket that fits the target insert."""
    if env._stage == 0:
        scores = [(env.w["safety"] * float(r["safety"]) + env.w["durability"] * float(r["p_durable"]))
                  for _, r in env.cands.iterrows()]
        return int(np.argmax(scores))
    if env._stage == 1:
        reachable = env.writer_options()
        best = max(reachable, key=lambda f: env.activity.get(f, 0.0))
        return WRITER_FAMILIES.index(best)
    fits = [i for i, b in enumerate(CARGO_BUCKETS) if b >= env.cargo_bp] or [len(CARGO_BUCKETS) - 1]
    return fits[0]


def rollout(env: "GenomeWritingEnv", policy, seed: int = 0) -> dict:
    """Run one episode under `policy`; return the final reward + the assembled plan."""
    rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    total, term, info = 0.0, False, {}
    while not term:
        a = policy(env, obs, rng)
        obs, r, term, _trunc, info = env.step(a)
        total += r
    return {"reward": round(total, 4), "plan": env.plan(), "terminal_info": info}


def compare_policies(seed: int = 0) -> dict:
    """Run the random and greedy(planner) policies on the same env — the interface smoke test. The greedy
    policy is the deterministic optimum; RL is NOT claimed to beat it (near-one-shot decision)."""
    env = GenomeWritingEnv(seed=seed)
    rnd = rollout(env, random_policy, seed=seed)
    grd = rollout(GenomeWritingEnv(seed=seed), greedy_planner_policy, seed=seed)
    return {"random": rnd, "greedy_planner": grd,
            "greedy_at_least_random": bool(grd["reward"] >= rnd["reward"]),
            "note": "interface only — greedy(planner) is the deterministic optimum; no RL superiority claimed."}
