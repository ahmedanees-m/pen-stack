"""Gymnasium environment for genome-write planning (v3.4, WS-ENV), the train/eval surface.

v3.2 shipped a *thin* interface (insertion only). v3.4 hardens it into a **full environment** whose state is
a partial design across **all v3.3 write types**, whose every action is checked by the **rule-grounded
verifier** (`pen_stack.verify.verify`), and whose reward is the **legal, calibrated plan score** (the planner
objective scaled by the L4 calibrated confidence, minus soft-rule penalties). An episode is a complete legal
plan **or a justified refusal** (an explicit abstain action):

    stage 0: WRITE TYPE -> stage 1: SITE -> stage 2: WRITER family ->
    stage 3: CARGO bucket -> stage 4: DELIVERY vehicle -> terminate (verify -> reward)

At any stage the agent may take the reserved **abstain** action (``action == action_space.n - 1``) and end
the episode with a refusal: refusing beats committing to an *illegal* plan (refusal reward > illegal penalty),
but a good legal plan beats refusing, the contract that makes "abstention over guessing" measurable.

**Explicitly an INTERFACE + EVALUATION HARNESS, not an RL-superiority claim.** The genome-writing decision is
near-one-shot; the greedy(planner) policy *is* the deterministic optimum and is the reference. No learned
policy is claimed to beat it (the `greedy >= random` check is a sanity test, not a result). Behind the
optional ``[env]`` extra (gymnasium); the rest of PEN-STACK does not import this module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import gymnasium as gym
    from gymnasium import spaces
    _HAVE_GYM = True
except Exception: # noqa: BLE001 - gymnasium only in the [env] extra
    _HAVE_GYM = False
    gym = None
    spaces = None

from pen_stack.planner.optimize import (
    EditIntent,
    load_intent_weights,
    writer_activity_by_family,
)

WRITE_TYPES = ["insertion", "excision", "inversion", "replacement",
               "regulatory_rewrite", "landing_pad_install", "multiplex"]
WRITER_FAMILIES = ["bridge_IS110", "seek_IS1111", "CAST_VK", "serine_integrase",
                   "PE_integrase", "Cas9", "Cas12a"]
# writers whose output is DNA (AAV/lenti/HDAd-compatible). Cas9/Cas12a deliver RNP.
_DNA_WRITERS = ["bridge_IS110", "seek_IS1111", "CAST_VK", "serine_integrase", "PE_integrase"]
CARGO_BUCKETS = [1000, 3000, 6000, 12000, 30000] # bp
_N_STAGES = 5

# reward shaping constants (pre-registered in prereg/ws_env.yaml)
_ILLEGAL_PENALTY = -1.0 # committing to an illegal plan is the worst outcome
_ABSTAIN_REWARD = 0.05 # a justified refusal beats an illegal plan, loses to a good legal one
_SOFT_PENALTY = 0.1 # per soft-rule flag (e.g. split-AAV efficiency)
_CARGO_SHORT_PENALTY = 0.1 # chosen bucket smaller than the target insert


def delivery_vehicles() -> list[str]:
    from pen_stack.planner.delivery_vehicles import names
    return list(names())


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


def writer_form(family: str | None) -> str:
    """DNA for integrase/recombinase/prime-editor writers; RNP for Cas9/Cas12a."""
    return "DNA" if family in _DNA_WRITERS else "RNP"


class GenomeWritingEnv(_base()):
    """Full Gymnasium environment over the v3.3 router + verifier (see module docstring).

    State = partial design; actions build it stage by stage; the terminal reward is the verifier's legality
    gate times the L4 calibrated plan confidence. The reserved abstain action ends the episode with a refusal.
    """
    metadata = {"render_modes": []}

    def __init__(self, candidates: pd.DataFrame | None = None,
                 intent: str | EditIntent = "safe_harbour_insertion", cargo_bp: int = 3000, seed: int = 0):
        if not _HAVE_GYM:
            raise ImportError("GenomeWritingEnv needs the optional [env] extra: pip install pen-stack[env]")
        super().__init__()
        self.cands = (candidates if candidates is not None else demo_candidates(seed=seed)).reset_index(drop=True)
        self.intent = EditIntent(intent) if not isinstance(intent, EditIntent) else intent
        self.cargo_bp = int(cargo_bp) # target insert size the plan must accommodate
        self.w = load_intent_weights()["intents"][self.intent.value]
        self.activity = writer_activity_by_family()
        self.vehicles = delivery_vehicles()
        self.n_sites = len(self.cands)
        self._stage_sizes = [len(WRITE_TYPES), self.n_sites, len(WRITER_FAMILIES),
                             len(CARGO_BUCKETS), len(self.vehicles)]
        # one fixed Discrete space sized to the largest stage + 1 reserved ABSTAIN action.
        self._abstain = max(self._stage_sizes)
        self.action_space = spaces.Discrete(self._abstain + 1)
        # observation: [stage_frac, write_type_frac, site_safety, site_p_durable, writer_activity,
        # cargo_frac, delivery_cap_frac, legal_flag]
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(8,), dtype=np.float32)
        self._rng = np.random.default_rng(seed)
        self.reset(seed=seed)

    # ---- helpers -------------------------------------------------------------------------------
    def _obs(self) -> np.ndarray:
        site = self.cands.iloc[self._site] if self._site is not None else None
        cap = 0.0
        if self._delivery:
            from pen_stack.planner.delivery_vehicles import vehicle
            c = (vehicle(self._delivery) or {}).get("cargo_capacity_bp")
            cap = min(1.0, (c or 0) / 100000.0)
        return np.array([
            self._stage / _N_STAGES,
            (WRITE_TYPES.index(self._write_type) / len(WRITE_TYPES)) if self._write_type else 0.0,
            float(site["safety"]) if site is not None else 0.0,
            float(site["p_durable"]) if site is not None else 0.0,
            float(self.activity.get(self._writer, 0.0)) if self._writer else 0.0,
            (self._cargo / max(CARGO_BUCKETS)) if self._cargo else 0.0,
            cap,
            1.0 if self._legal else 0.0,
        ], dtype=np.float32)

    def site_options(self) -> list[int]:
        return list(range(self.n_sites))

    def writer_options(self) -> list[str]:
        """Writer families reachable at the chosen site (tier-1 reachability), or all if no site yet."""
        if self._site is None:
            return WRITER_FAMILIES
        return [f for f in str(self.cands.iloc[self._site]["reachable_tier1"]).split(";") if f] or WRITER_FAMILIES

    def _build_design(self):
        from pen_stack.rules import Design
        site = self.cands.iloc[self._site] if self._site is not None else None
        return Design(
            write_type=self._write_type or "insertion",
            writer_family=self._writer,
            writer_output_form=writer_form(self._writer),
            cargo_bp=self._cargo,
            delivery_vehicle=self._delivery,
            edit_intent=self.intent.value,
            chrom=str(site["chrom"]) if site is not None else None,
            # per-axis scores let the verifier attach a CALIBRATED confidence (no fabrication otherwise)
            safety=float(site["safety"]) if site is not None else None,
            p_durable=float(site["p_durable"]) if site is not None else None,
            writer_activity=float(self.activity.get(self._writer, 0.4)),
        )

    # ---- Gymnasium API -------------------------------------------------------------------------
    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed) # seeds gymnasium's self.np_random (env-checker contract)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._stage = 0
        self._write_type = None
        self._site = None
        self._writer = None
        self._cargo = None
        self._delivery = None
        self._legal = False
        self._refused = False
        return self._obs(), {"stage": "write_type"}

    def step(self, action: int):
        action = int(action)
        reward, terminated, info = 0.0, False, {}
        if action == self._abstain: # justified refusal -> end episode
            self._refused = True
            terminated = True
            reward = _ABSTAIN_REWARD
            info = {"stage": "refused", "abstained": True,
                    "note": "refusal beats an illegal plan; loses to a good legal one"}
            self._stage += 1
            return self._obs(), float(reward), True, False, info

        if self._stage == 0: # choose WRITE TYPE
            self._write_type = WRITE_TYPES[action % len(WRITE_TYPES)]
            info = {"stage": "site", "chose_write_type": self._write_type}
        elif self._stage == 1: # choose SITE
            self._site = self.site_options()[action % self.n_sites]
            info = {"stage": "writer", "chose_site": int(self._site)}
        elif self._stage == 2: # choose WRITER family
            self._writer = WRITER_FAMILIES[action % len(WRITER_FAMILIES)]
            info = {"stage": "cargo", "chose_writer": self._writer,
                    "writer_reachable": self._writer in self.writer_options()}
        elif self._stage == 3: # choose CARGO bucket
            self._cargo = CARGO_BUCKETS[action % len(CARGO_BUCKETS)]
            info = {"stage": "delivery", "chose_cargo_bp": self._cargo}
        elif self._stage == 4: # choose DELIVERY vehicle -> terminate
            self._delivery = self.vehicles[action % len(self.vehicles)]
            reward, info = self._verified_reward()
            terminated = True
            info = {"stage": "done", "chose_delivery": self._delivery, **info, **self.plan()}
        self._stage += 1
        return self._obs(), float(reward), bool(terminated), False, info

    # ---- reward = legality gate x calibrated plan score ----------------------------------------
    def _verified_reward(self) -> tuple[float, dict]:
        from pen_stack.verify import verify
        design = self._build_design()
        v = verify(design)
        site = self.cands.iloc[self._site]
        base = (self.w["safety"] * float(site["safety"])
                + self.w["durability"] * float(site["p_durable"])
                + self.w["activity"] * float(self.activity.get(self._writer, 0.4)))
        meta = {"legal": v.legal, "deferred": v.deferred, "confidence": v.confidence,
                "violations": [x["rule_id"] for x in v.violations],
                "soft_flags": [s["rule_id"] for s in v.soft_flags]}
        if v.deferred: # unsupported/ambiguous write type -> a deterministic refusal
            self._refused = True
            return _ABSTAIN_REWARD, {**meta, "note": "router deferred (unsupported write type)"}
        if not v.legal: # committed to an illegal plan -> worst outcome
            self._legal = False
            return _ILLEGAL_PENALTY, meta
        self._legal = True
        conf = v.confidence if v.confidence is not None else 0.5
        reward = base * (0.5 + 0.5 * conf) - _SOFT_PENALTY * len(v.soft_flags)
        if self._cargo is not None and self._cargo < self.cargo_bp:
            reward -= _CARGO_SHORT_PENALTY
        return float(reward), meta

    def plan(self) -> dict:
        return {"write_type": self._write_type,
                "site": None if self._site is None else int(self._site),
                "writer": self._writer, "cargo_bp": self._cargo, "delivery": self._delivery,
                "intent": self.intent.value, "legal": self._legal, "refused": self._refused}


# re-export the reference policies + rollout helpers (defined in policies.py) for backward-compatible imports
from pen_stack.env.policies import ( # noqa: E402
    compare_policies,
    greedy_planner_policy,
    random_policy,
    rollout,
)

__all__ = ["WRITE_TYPES", "WRITER_FAMILIES", "CARGO_BUCKETS", "GenomeWritingEnv", "demo_candidates",
           "delivery_vehicles", "writer_form", "random_policy", "greedy_planner_policy", "rollout",
           "compare_policies"]
