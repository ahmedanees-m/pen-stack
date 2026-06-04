# Genome-Writing Bench v0.1 - Leaderboard

Tasks: **6/6 available** in this run (unavailable = needs the Phase-1 atlas / Perry tables / an LLM, which run on the VM/local).
Deterministic planner beats the naive baseline on **3/3** grounded tasks with a baseline.

| Solver | Tasks scored | Beats naive | No-fabrication | Note |
|---|---|---|---|---|
| deterministic_planner | 6 | 3/3 | n/a (deterministic) | validated planning tools - the reference |
| naive_baseline | 3 | - | n/a (deterministic) | safety-only / prevalence / Hamming baselines |
| llm_agent | 2 | = planner (grounded) | PASS | LLM orchestrator (nvidia) - LLM-driven on 2/2 goals; 14 grounded tool calls, 0 fabricated. Reaches the planner's numbers only by grounding every value. |

## Per-task results
| Task | Family | Available | Planner | Naive baseline | Gate |
|---|---|---|---|---|---|
| site_selection_blind_gsh | T1_site_selection | True | 0.9192 | 0.5 | - |
| writer_family_recovery | T2_writer_selection | True | 1.0 | 0.25 | - |
| within_locus_ranking | T3_within_locus | True | 0.5 | None | - |
| bridge_offtarget_discrimination | T4_offtarget | True | 0.7683 | 0.6213 | - |
| intent_specification_compliance | T5_intent_compliance | True | 7 | None | - |
| agent_no_fabrication | T6_no_fabrication | True | True | None | PASS |

Scope: tasks are bounded by available documented writes (small, survivorship-biased). The bench measures grounded planning quality and site/writer/off-target discrimination, not clinical outcome. No task is scored against a circular label (Gate G-A).