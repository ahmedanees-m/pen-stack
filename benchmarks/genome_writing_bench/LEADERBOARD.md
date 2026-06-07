# Genome-Writing Bench v0.1 - Leaderboard

Tasks: **7/7 available** in this run (unavailable = needs the Phase-1 atlas / Perry tables / an LLM, which run on the VM/local).
Deterministic planner beats the naive baseline on **3/3** grounded tasks with a baseline.

| Solver | Tasks scored | Beats naive | No-fabrication | Note |
|---|---|---|---|---|
| deterministic_planner | 7 | 3/3 | n/a (deterministic) | validated planning tools - the reference |
| naive_baseline | 3 | - | n/a (deterministic) | safety-only / prevalence / Hamming baselines |

## Per-task results
| Task | Family | Available | Planner | Naive baseline | Gate |
|---|---|---|---|---|---|
| site_selection_blind_gsh | T1_site_selection | True | 0.7016 | 0.5075 | - |
| writer_family_recovery | T2_writer_selection | True | 0.8571 | 0.2857 | - |
| within_locus_ranking | T3_within_locus | True | 0.6 | None | - |
| bridge_offtarget_discrimination | T4_offtarget | True | 0.7683 | 0.6213 | - |
| intent_specification_compliance | T5_intent_compliance | True | 7 | None | - |
| agent_no_fabrication | T6_no_fabrication | True | True | None | PASS |
| ungrounded_llm_contrast | T7_ungrounded_contrast | True | 2 | None | - |

## Ungrounded-LLM contrast (T7) - what grounding actually buys
Same models, **no tools**, same write-planning goals. A concrete value for a tool-only field is a fabrication; an explicit refusal is honest. Two prompt conditions: **naive** (no anti-fabrication coaching - the realistic probe) and **coached** (explicitly told to refuse ungroundable values). The grounded agent is 0.0 under BOTH by construction - that architectural guarantee is the point; prompt-coaching is not a substitute for grounding.

| Agent | Prompt | Plan-goal fabrication | Ungroundable-goal fabrication |
|---|---|---|---|
| grounded PEN-Agent (with tools) | any | **0.0** | **0.0** |
| ungrounded qwen2.5_7b (no tools) | naive | 1.0 | 1.0 |
| ungrounded qwen2.5_7b (no tools) | coached | 0.0417 | 0.0 |
| ungrounded nemotron (no tools) | naive | 1.0 | 0.6667 |
| ungrounded nemotron (no tools) | coached | 0.0 | 0.0 |

_with tools the agent fabricates nothing (0.0 by construction, any prompt); without tools the SAME models fabricate tool-only values under a naive prompt, and even under explicit anti-fabrication coaching they still slip - so grounding, not prompting, is what removes fabrication. The benchmark now separates grounded from ungrounded agents._

Scope: tasks are bounded by available documented writes (small, survivorship-biased). The bench measures grounded planning quality and site/writer/off-target discrimination, not clinical outcome. No task is scored against a circular label (Gate G-A).