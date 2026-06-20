# Integrate PEN-STACK in your AI (v6.1)

PEN-STACK is a **grounding substrate** an AI agent can depend on. From v6.1 the AI-facing surface is
**self-describing**: an agent can ask, programmatically, *"what can you do, and what do you refuse to answer?"*,
and get a typed answer it can route on. Integrate in minutes over REST or MCP.

## The four guarantees

When your agent calls PEN-STACK, every answer carries:

1. **Rule-grounded legality**: a design is legal/illegal per machine-readable rules, with the *named* rule cited.
2. **Calibrated confidence**: soft scores come with conformal intervals; out-of-distribution is flagged.
3. **Explicit scope**: what PEN-STACK *cannot* tell you is returned as data (`out_of_scope` / `extrapolating`), never guessed.
4. **Biosecurity safety**: a dual-use/hazardous design is refused or escalated, as a structured verdict.

…and **no fabrication**: every number is computed by a validated tool.

## Discover capabilities and scope (the differentiator)

```bash
GET /capabilities      # machine-readable: the tools, inputs, outputs, stability
GET /scope             # machine-readable: the known-unknowns + every oracle's in-distribution envelope
```

`/scope` is the contract that makes depending on PEN-STACK safe: it lists, as data, the questions PEN-STACK
**refuses** to answer (phenotype, in-vivo immunogenicity magnitude, long-term clinical durability, …) and what
each wrapped model is *not* valid for. Your agent reads it and never builds on a non-answer.

```python
from pen_stack.api import capability_manifest, scope_manifest   # in-process
caps = capability_manifest()      # {"tools": [...], "guarantees": [...], "stability": "stable"}
scope = scope_manifest()          # {"known_unknowns": [...], "oracle_scope_cards": [...], "policy": "..."}
```

## REST: the golden path

```python
import requests
BASE = "http://localhost:8000"            # uvicorn pen_stack.server.api:app

scope = requests.get(f"{BASE}/scope").json()
v = requests.post(f"{BASE}/verify", json=design).json()
if v["safety"]["decision"] == "refuse":   # safety branch: halt
    ...
elif not v["legal"]:                      # legality branch: revise
    ...
else:                                     # proceed, with calibrated confidence + immune profile
    use(v["confidence"], v["immune_profile"])
```

Tool routes: `/verify · /safety · /immune · /generate · /predict · /suggest · /session` + `/capabilities · /scope`.
The full typed contract is the auto-generated **OpenAPI 3.1** spec at `/openapi.json`. Runnable example:
[`examples/external_agent.py`](../examples/external_agent.py).

## MCP: call PEN-STACK from any MCP client

```bash
python -m pen_stack.agent.mcp_server      # fastmcp; tools + the capabilities/scope resources
```

Tools: `verify_write · safety_screen · immune_profile · generate_designs · predict_outcome · suggest_experiment
· co_scientist_session · graph_query · plan_write · …`. Resources: `pen-stack://capabilities`,
`pen-stack://scope`. A hazardous design returns a **structured refusal** (`safety.decision == "refuse"`) an agent
branches on. Runnable example: [`examples/mcp_client.py`](../examples/mcp_client.py).

## Drop into any tool-calling framework

[`examples/agent_tools.py`](../examples/agent_tools.py) builds OpenAI/Anthropic-shaped tool specs **from the live
capability manifest** (so they never drift from the code) and dispatches to the validated engine in-process:

```python
from examples.agent_tools import tool_specs, dispatch
specs = tool_specs()                                  # hand to LangChain / the OpenAI or Anthropic SDK
result = dispatch("verify_write", {"payload": {...}}) # numbers come only from the engine
```

## Stability

All exposed contracts (the manifests, the OpenAPI schemas, the MCP tool/resource shapes) are versioned and
deprecation-policed under the **1.0 commitment**; see [API stability](STABILITY.md). The
`OracleResult`/`Verdict`/`SafetyVerdict`/immune-profile contracts and invariants are stable across 6.x.

## The bottleneck

This surface makes integration **easy and dependable**; it does not, by itself, create adoption. Landing a first
external integration and a demonstrated real-world result remain the standing outreach work. The surface is
shipped; `benchmarks/genome_writing_challenge/SUBMISSIONS.md` records external entries as they arrive.
