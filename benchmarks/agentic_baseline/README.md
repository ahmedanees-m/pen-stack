# Agentic baseline: an external LLM agent drives the tools (audited for no-fabrication)

The no-fabrication invariant is often stated as "0 by construction". This benchmark makes it *operational*:
a **real external LLM agent** (not the deterministic state machine) plans a genome-writing goal and **calls
the validated design tools itself**, and we audit that every number in its returned plan is traceable to a
tool result.

## Result (`metrics.json`)

Four write-planning goals (CAR knock-in at TRAC; durable cassette at AAVS1; CCR5 for HIV resistance; durable
transgene at CLYBL), run by three models spanning the capability range:

| Agent | hosting | LLM in control | goals with a tool call | no-fabrication | total tool calls |
|---|---|---|---|---|---|
| **Nemotron-120B** | NVIDIA cloud | 4/4 | 2/4 | PASS | 10 |
| **Claude (Haiku-4.5)** | Anthropic cloud | 4/4 | 3/4 | PASS | 12 |
| **Qwen2.5-1.5B** | local Ollama (CPU) | 4/4 | 4/4 | PASS | 15 |
| deterministic gate (no LLM) | - | 8/8 goals | 8/8 | PASS | - |

The two middle columns measure different things and the distinction matters. The LLM orchestrator was in
control on every goal rather than falling back to the deterministic path, and the no-fabrication audit passed
in every run: every quantity that was emitted equalled a direct tool call. But tool engagement was uneven. 9
of the 12 model-goal runs issued at least one call to `plan_write`, `writability`, `reachable_writers`,
`writer_axes` or another validated tool; the other 3 answered in prose, emitted no quantity, and so passed
with nothing audited.

**What this establishes, and what it does not.** It establishes that no ungrounded quantity was emitted. It
does not establish that the tools were driven throughout, and a pass obtained by answering in prose is not
evidence of grounded task completion. Read the audit alongside the engagement column, and see the matched run
over the full goal set, which reports task completion as a separate endpoint.

**The architectural point stands on the runs that did engage:** a 1.5B local model and a 120B hosted model
both emitted only tool-derived quantities, because a quantity that no tool produced cannot be represented.

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

Four goals x three models is a focused baseline, not a leaderboard. It measures a tool-using LLM agent
operating the substrate under the no-fabrication audit, across a local 1.5B model and two hosted models. It
is smaller than the 240-field prompt-only probe and its engagement is uneven, so it is reported with the
engagement column above rather than as a standalone rate. The complementary LLM-off-tools contrast, an
ungrounded model fabricating the same quantities, is in `benchmarks/grounding_llm_on/`.
