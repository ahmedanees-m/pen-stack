# PEN-Agent — grounded write-planning agent (v3.1, WS-E2)

PEN-Agent turns a genome-writing goal into an auditable plan by orchestrating PEN-STACK's **validated
tools**. Its contribution is not a new model — it is the **grounding**: every number it reports is copied
from a tool result and tagged with provenance, and anything it cannot ground is **refused or degraded, never
invented**. It is scored on the Genome-Writing Bench (task T6, a hard gate) and ships only if it does not
fabricate (Gate G-E).

## Two layers

| Layer | File | Role |
|---|---|---|
| **Deterministic state machine** | `pen_stack/agent/pen_agent.py` | Sequences the validated tools; the no-fabrication guarantee holds *by construction* (values are copied from tool dicts). Runs with **no LLM**. |
| **LLM orchestrator** | `pen_stack/agent/orchestrator.py` | An optional conversational front-end. The LLM may obtain numbers **only** by calling the registered tools (`agent/tools.py`); the eval audits that every number in its trace equals a direct tool call. |

The LLM is **non-load-bearing**: with no provider reachable, the agent falls back to the deterministic path
and the plan is unchanged. Provider config is `configs/llm.yaml` (VM: local Ollama 7B; laptop/fallback:
hosted Nemotron).

## State machine

```
goal intake → site selection (writability) → writer selection (reachability/activity)
            → cargo design (+ Cargo Polish) → off-target → 3D structural risk → report
```

Each step yields `{name, tool, status, provenance, result, reason}` where `status ∈ {ok, degraded, refused}`:

- **ok** — the tool grounded the value; `provenance` names the tool (e.g. `wgenome.writability`,
  `planner.pipeline`, `bridge.offtarget`, `wgenome.structure3d`).
- **degraded** — the signal is unavailable here (e.g. AlphaGenome contact map not cached, or off-target
  applies only to bridge/seek writers). Reported with a reason; never guessed. The agent keeps going.
- **refused** — a prerequisite is missing (e.g. no writable locus / no Phase-1 atlas). The agent stops that
  branch rather than invent a plan.

### Modes

- `automatic` — run all steps and return the full plan.
- `guided` — pause after writer selection (the human reviews before cargo/off-target/3D).
- `qa` — single-tool question answering.

## Use it

```python
from pen_stack.agent.pen_agent import plan_write_session
r = plan_write_session("TRAC", "knock_in_with_disruption", cargo_bp=2000, ct="k562",
                       payload_seq="ATG...")           # payload_seq adds Cargo Polish
# r["no_fabrication"] is True; r["provenance"] maps each grounded step to its tool;
# r["degraded_modes"] / r["refusals"] carry reasons.

# No-fabrication hard gate (deterministic, used by the bench T6):
from pen_stack.agent.pen_agent import no_fabrication_audit
no_fabrication_audit()["all_no_fabrication_pass"]      # True
```

### Via MCP (external agents)

`pen_stack/agent/mcp_server.py` exposes the validated tools **and** `plan_write_session` over the Model
Context Protocol, so any MCP client (Claude, etc.) can drive the grounded planner. The same functions back
the in-process agent and the eval harness, so an external agent gets identical, grounded numbers.

### On the bench

```bash
python bench/run.py --agent      # deterministic gate + the REAL LLM orchestrator when a provider is reachable
```

The leaderboard's `llm_agent` row is the real LLM driving the tools through the orchestrator; it can only
reach the deterministic planner's numbers by grounding every value, and it is disqualified if it fabricates.

## Guarantees & scope

- **No fabrication (hard gate):** outputs that cannot be grounded in a tool result are refused. Verified by
  `validate/agent_eval.py::no_fabrication` (LLM trace) and `pen_agent.no_fabrication_audit` (state machine).
- **Provenance:** every recommendation carries its source (tool / model / DOI).
- **Degraded mode:** functions when AlphaGenome or the bridge engine is unavailable.
- **Scope:** a grounded orchestration layer over the validated core — not a new model, and not clinical
  advice (every plan carries the decision-support disclaimer).
