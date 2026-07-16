# Agentic baseline: an external LLM agent drives the tools (audited for no-fabrication)

The no-fabrication invariant is often stated as "0 by construction". This benchmark makes it *operational*:
a **real external LLM agent** (not the deterministic state machine) plans a genome-writing goal and **calls
the validated design tools itself**, and we audit that every number in its returned plan is traceable to a
tool result. This is the reviewer-requested agentic baseline on our own bench.

## Result (`metrics.json`)

Four write-planning goals (CAR knock-in at TRAC; durable cassette at AAVS1; CCR5 for HIV resistance; durable
transgene at CLYBL), run by three models spanning the capability range:

| Agent | hosting | LLM-driven | no-fabrication | total tool calls |
|---|---|---|---|---|
| **Nemotron-120B** | NVIDIA cloud | 4/4 | PASS | 10 |
| **Claude (Haiku-4.5)** | Anthropic cloud | 4/4 | PASS | 12 |
| **Qwen2.5-1.5B** | local Ollama (CPU) | 4/4 | PASS | 15 |
| deterministic gate (no LLM) | - | 8/8 goals | PASS | - |

Every model **drove the loop itself** (`llm_driven = 4/4`) - calling `plan_write`, `writability`,
`reachable_writers`, `writer_axes`, and the other validated tools - and the **no-fabrication audit passed for
all**: every quantity in every trace equalled a direct tool call. A goal answered in prose (0 tool calls on
that goal) still passes, because it emits no ungrounded number.

**The point:** grounding is enforced by the *architecture*, not the model. A 1.5B local model and a frontier
120B model both fabricate nothing when quantities must be routed through the tools - which is exactly what a
no-fabrication substrate should guarantee.

## Reproduce

```bash
# set a reachable provider in configs/llm.yaml (nvidia | anthropic | ollama | ollama_small), key in the
# gitignored configs/<provider>_api_key.txt or the matching env var, then:
python bench/run.py --agent
```

`run_agent_solver()` runs the deterministic gate (always) plus the live LLM orchestrator when a provider is
reachable. The LLM layer is provider-agnostic (`pen_stack/rag/llm.py`: openai / ollama / anthropic styles),
so any of the three models above drives the same tool loop.

## Scope

Four goals x three models is a focused baseline, not a leaderboard. It answers the specific question a
*GigaScience* reviewer asks - "compare to an agentic system on your own bench" - by showing a real tool-using
LLM agent (local and frontier) operating the substrate under the no-fabrication audit. The complementary
LLM-*off*-tools contrast (an ungrounded model fabricating the same quantities) is in
`benchmarks/grounding_llm_on/`.
