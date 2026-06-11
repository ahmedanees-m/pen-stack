# Genome-Writing Bench v0.3.3 - Leaderboard

Tasks: **17/17 available** in this run (unavailable = needs the Phase-1 atlas / Perry tables / an LLM, which run on the VM/local).
Deterministic planner beats the naive baseline on **13/13** grounded tasks with a baseline.

| Solver | Tasks scored | Beats naive | No-fabrication | Note |
|---|---|---|---|---|
| deterministic_planner | 17 | 13/13 | n/a (deterministic) | validated planning tools - the reference |
| naive_baseline | 13 | - | n/a (deterministic) | safety-only / prevalence / Hamming baselines |

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
| calibration_coverage | T8_calibration | True | 1.0 | 0.0 | - |
| selective_prediction_usefulness | T9_selective_pred | True | 0.9300087489063867 | 0.7393510014869238 | - |
| ood_honesty | T10_ood_honesty | True | 1.0 | 0.0 | - |
| out_of_scope_refusal | T11_out_of_scope | True | 1.0 | 0.0 | - |
| rule_grounded_legality | T12_rule_legality | True | 1.0 | 0.0 | - |
| multi_write_type_legality | MW_multi_write_type | True | 1.0 | 0.0 | - |
| adversarial_robustness | T13_scope_disguise | True | 1.0 | 0.0 | - |
| graph_multihop_reasoning | GR_graph_reasoning | True | 1.0 | 0.0 | - |
| co_scientist_grounded | CS_co_scientist | True | 1.0 | 0.0 | - |
| safety_screening | SF_safety_screening | True | True | False | PASS |

## Trust tasks (T8-T11) - calibration + scope-awareness separate *trustworthy* agents
Each contrasts the **uncertainty-aware** agent (conformal coverage, selective prediction, OOD flagging, out-of-scope deferral) with an **over-confident** baseline (an uncalibrated interval, no abstention, never flags OOD, no scope layer). The over-confident agent is the realistic failure mode a calibrated co-scientist must beat.

| Task | Family | Available | Uncertainty-aware | Over-confident baseline |
|---|---|---|---|---|
| calibration_coverage | coverage within tol | True | 1.0 | 0.0 |
| selective_prediction_usefulness | accuracy (high-conf decile) | True | 0.9300087489063867 | 0.7393510014869238 |
| ood_honesty | OOD flag rate | True | 1.0 | 0.0 |
| out_of_scope_refusal | deferral rate | True | 1.0 | 0.0 |

_Uncertainty-aware beats the over-confident baseline on **4/4** available trust tasks - the calibration is not merely present, it is useful and legible._

## Robustness tasks (v0.3) - multi-write-type + adversarial probes separate *robust* agents
The verifier-backed agent routes every write type to its rule sub-graph and survives adversarial probes built to break a naive agent (out-of-scope-in-disguise, contradictory constraints, prompt injection, distribution shift). The over-confident ungrounded baseline has no router/rule base, obeys the injection, and ignores OOD.

| Task | Family | Available | Verifier-backed | Over-confident baseline |
|---|---|---|---|---|
| multi_write_type_legality | MW_multi_write_type | True | 1.0 | 0.0 |
| adversarial_robustness | T13_scope_disguise | True | 1.0 | 0.0 |

_Verifier-backed beats the over-confident baseline on **2/2** available robustness tasks; no-fabrication holds throughout (incl. under prompt injection)._

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