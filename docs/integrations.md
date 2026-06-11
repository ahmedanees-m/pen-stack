# Integrations & adoption (v5.13)

PEN-STACK exposes two integration surfaces so a general AI scientist or a lab can call it, and so external agents
can enter the Genome-Writing Challenge.

## 1. MCP — call PEN-STACK from any MCP client

PEN-STACK ships an MCP server (`pen_stack/agent/mcp_server.py`) registering the validated tools. Any MCP client
(Claude, a Co-Scientist/Robin-class agent, …) can call them:

```bash
python -m pen_stack.agent.mcp_server      # starts the MCP server (fastmcp)
```

Tools include `writability`, `reachable_writers`, `writer_axes`, `plan_write`, `ask_literature`,
`multiplex_translocation_risk`, and the v3.3+ `verify_write` (legality + reasons + confidence + scope + safety +
immune profile). Every number a client gets back is tool-sourced — the no-fabrication gate holds across the
boundary.

## 2. The co-scientist over the full loop

```python
from pen_stack.agent.co_scientist import co_scientist_session
session = co_scientist_session(goal, cell_state="k562")
# -> strategies (Pareto, incl. immune axis), predicted_outcomes (calibrated),
#    immune_profiles (per-axis, first-class), suggested_experiments, citations,
#    scope_ledger, safety. The scientist/lab decides; the co-scientist drives.
```

See [The co-scientist over the loop](co_scientist_loop.md).

## 3. Submit to the Genome-Writing Challenge

```python
from benchmarks.genome_writing_challenge.harness import Submission, evaluate

def my_predict(public_input):                       # public_input has NO label
    fam = public_input["family"]
    if fam == "legality":    return True
    if fam == "safety":      return "clear"
    if fam == "immune_risk": return "genotoxicity"
    return None

print(evaluate(Submission("my-agent", my_predict), round_id="2026R1"))
```

The reference (`reference_submission()`) anchors the leaderboard. See
[`benchmarks/genome_writing_challenge/README.md`](../benchmarks/genome_writing_challenge/README.md).

## The standing adoption bottleneck (honest)

A standard requires a community. PEN-STACK provides the **open, reproducible, held-out benchmark** and the
**integration surface** (MCP + submission API + a worked reference example); landing **≥1 external integration**
and **≥1 external submission** depends on outreach — the non-code bottleneck flagged since v3.1. The surface is
shipped and documented so a partner can integrate in minutes; `SUBMISSIONS.md` is updated as external entries
arrive.
