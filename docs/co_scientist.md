# The co-scientist (v5.0)

v5.0 matures the reasoning layer on top of the verifier (v3.3), the environment (v3.4), the oracle mesh
(v4.0), and the living world-model (v4.5). Give it a goal and an intent and it returns a small set of
**materially distinct, ranked, fully-traceable strategies** — each verified, calibrated, cited, and
scope-ledgered — while the **no-fabrication guarantee holds by construction**: the reasoning layer proposes
and critiques, but every number still comes from a validated tool or oracle.

> **The central invariant.** Intelligence rises while groundedness never falls. A test asserts no-fabrication
> across the *full* reasoning stack (`pen_stack/validate/bench_coscientist_tasks.py`).

## What it does (`pen_stack/agent/co_scientist.py`, `pen_stack/agent/cite.py`)

| Capability | Function | Guarantee |
|---|---|---|
| **Multiple distinct strategies** | `propose_strategies(goal)` | 2–3 strategies differing on ≥2 design axes (write-type / writer / delivery / intent) — *materially* distinct, not reworded (`distinctness()` measures it); each independently **legal** + **confidence-tagged** |
| **Deliberative planning** | `deliberate(goal)` | the deliberative planner vs the deterministic `pen_agent` baseline, head-to-head; both grounded |
| **Self-critique / revise** | `critique_and_revise(design)` | the critic only flags + suggests a design-level swap (never invents a number); the revision is **re-verified**; falsifiable — it improves flawed plans (illegal→legal) and never spuriously touches clean ones (`critique_falsifiability()`) |
| **Cited rationale** | `cited_rationale(design)` | the "why" cites DOIs **drawn from the curated world-model** (so they resolve by construction); a hallucinated-citation guard rejects any DOI not in the curated set |
| **Scope ledger** | `scope_ledger(design)` | per recommendation, an itemised list of what **was** assessed (legality / reachability / delivery / payload / calibrated confidence) and what was **not** (the standing known-unknowns) — never silently omitted |
| **Scoped generalisation** | `generalise(task)` | adjacent genetic-engineering tasks are **grounded-or-refused**: answered only if they map to an existing grounded capability, otherwise refused with a scope statement |

## Honest scope

A better reasoner is **not a complete model of the cell**. structure→phenotype, in-vivo behaviour,
immunogenicity magnitude, long-term durability and higher-order epistasis remain out of scope — the
co-scientist makes that boundary *legible* (the scope ledger), it does not close it. Self-critique and
multi-strategy ship only because they help on held-out checks, or are reported as not-yet-useful.
Generalisation is approached only as far as the grounding allows; the rest is refused, not faked.

See `prereg/ws_{plan,crit,cite}.yaml` and the `co_scientist_grounded` bench task (Genome-Writing Bench v0.3.2).
