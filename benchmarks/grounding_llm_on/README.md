# Grounding, LLM on: the ungrounded-baseline contrast

The no-fabrication invariant is a *structural* property: with the validated tools in the loop, every
reported quantity is copied from a tool result, so an ungrounded number cannot be represented. The
`chat_grounding` / `chat_safety` probe sets verify that invariant with the LLM **disabled**, to isolate the
routing-and-grounding architecture from any one model's behaviour.

This benchmark supplies the complementary, **LLM-on** contrast the invariant needs to be discriminating:
the *same* write-planning goals, asked of a live model with **no tools**. Any concrete value it emits for a
tool-only field (writability, safety, durability, off-target count, structural risk, target coordinate) is
necessarily ungrounded, i.e. fabricated; the only correct answer is to refuse.

## Result (`metrics.json`)

### Expanded probe: 40 planning goals + 30 ungroundable questions, three model families, LLM live

| Model (family) | naive prompt | coached prompt ("output REFUSE if you cannot ground it") |
|---|---|---|
| **Claude Haiku-4.5** (Anthropic, frontier) | fabricates **98.8%** of tool-only planning fields | **0%** |
| **Nemotron-120B** (NVIDIA, frontier) | **90.8%** | **0.8%** |
| **Qwen2.5-1.5B** (local Ollama) | **96.7%** | **1.7%** (still slips) |
| **grounded PEN-Agent** (tools in loop) | **0%** | **0%** |

On the 30 ungroundable questions (exact in-human/in-vivo outcomes no tool can produce) the naive fabrication
rates are similar: Claude 93.3%, Nemotron 89.4%, Qwen 93.3%.

**The finding is sharp: grounding, not prompting or model scale, removes fabrication.** Under a naive prompt
*even a frontier aligned model* (Claude) invents 99% of the tool-only quantities; a 120B model and a 1.5B
model do the same. Explicit anti-fabrication coaching helps unevenly - it drives Claude to 0 but the smaller
local model still slips (1.7%) - so prompting is not a reliable guardrail across models. The grounded agent
is 0 under either prompt because it copies every number from a validated tool call
(`pen_agent.no_fabrication_audit`), verified live in `benchmarks/agentic_baseline/`.

### Original probe (7 goals, retained for continuity)

Qwen2.5-7B and Nemotron both fabricate 100% of tool-only fields naively; coached, Qwen-7B still slips 4.2%.

## Reproduce

Transcripts are cached under `data/llm_bench_cache/` (committed) so the score replays offline, in CI, with
no live model or API key:

```bash
python -m pen_stack.validate.ungrounded_baseline          # offline replay of the original probe
# expanded probe: score the committed cache against benchmarks/grounding_llm_on/adversarial_goals.json
python bench/run.py --agent --ungrounded-live             # regenerate transcripts against live providers
```

`configs/llm.yaml` selects the provider (Anthropic / NVIDIA / Ollama). Keys are read from a gitignored file
or an env var and are never committed. The adversarial goal set (`adversarial_goals.json`) was produced by a
multi-angle generation pass and deduped.

## Scope

Three model families x 70 adversarial goals x two prompt conditions is a genuine *measured, multi-provider,
LLM-on* rate spanning local to hosted-frontier - not the by-construction tautology - though still short of a
few-hundred-query natural-traffic population sweep. The grounded-vs-ungrounded separation is the load-bearing
claim and it holds across every model tested.
