# The Genome-Writing Environment (v3.4, WS-ENV)

A [Gymnasium](https://gymnasium.farama.org/) environment that turns PEN-STACK into a place an AI agent can be
**trained and graded** on the genome-writing decision. It is the *learning/ranking* counterpart to the v3.3
**verifier** (the *checking* surface): every action is validated by the rule-grounded verifier, and the reward
is the **legal, calibrated plan score**.

> **Interface, not a claim.** The genome-writing decision is near-one-shot, so this is an *interoperability +
> evaluation* surface, **not** evidence that a learned policy beats the deterministic planner. The
> `greedy(planner)` policy *is* the deterministic optimum and is the reference; `greedy >= random` is a sanity
> check, not a result.

## Install

```bash
pip install "pen-stack[env]"     # pulls gymnasium
```

## The MDP

| | |
|---|---|
| **Observation** | `Box(0,1, shape=(8,))` = `[stage, write_type, site_safety, site_p_durable, writer_activity, cargo, delivery_capacity, legal_flag]` |
| **Action** | `Discrete(N)`; the **last index is a reserved ABSTAIN action** available at every stage |
| **Episode** | `write_type → site → writer_family → cargo_bucket → delivery_vehicle`, then the verifier scores the plan; OR abstain at any stage for a justified refusal |
| **Step validity** | the assembled `Design` is checked by `pen_stack.verify.verify`; an unsupported write type defers (router) → treated as a refusal |
| **Reward** | `illegal = -1.0`; `refusal = +0.05`; `legal = base·(0.5 + 0.5·confidence) − 0.1·soft_flags − 0.1·[cargo too small]` |

`base` is the intent-weighted blend of (safety, durability, writer-activity); `confidence` is the L4
calibrated plan confidence the verifier attaches. The contract makes **abstention over guessing** measurable: a
justified refusal beats an *illegal* plan but loses to a *good legal* one.

## Quick start

```python
from pen_stack.env.genome_writing_env import GenomeWritingEnv, compare_policies

env = GenomeWritingEnv(seed=0)
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(env.action_space.sample())

# reference policies (random + the deterministic greedy planner)
print(compare_policies(seed=0))
# -> {'random': {...}, 'greedy_planner': {...}, 'greedy_at_least_random': True, 'greedy_plan_legal': True, ...}
```

The environment conforms to `gymnasium.utils.env_checker.check_env`, so any RL library that speaks the
Gymnasium API can drive it. Reference policies live in `pen_stack/env/policies.py`.

## Scope & honesty

- The env is an **interface + evaluation harness**, not a claim that learning helps (near-one-shot decision).
- Legality is the verifier's rule decision (mechanistic screens, not activity guarantees); confidence is
  calibrated but **marginal and N-limited** (inherits v3.2).
- The synthetic `demo_candidates` table lets the env run without the Phase-1 atlas; real use passes the
  writability-atlas rows as `candidates`.

See also: `docs/verify.md` (the checking surface), `docs/rules.md` (the rule base), the pre-registered MDP in
`prereg/ws_env.yaml`, and the Genome-Writing Bench (`benchmarks/genome_writing_bench/`).
