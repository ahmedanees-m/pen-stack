# Genome-Writing Bench v0.2

The first benchmark for the **writing** side of genome engineering: *where* to write (site selection),
*what* writer to use, *how* to design the cargo, and *what off-target / structural risk* a write carries,
complementing the many editing-side (Cas9/base/prime) tools and benchmarks.

It is built into PEN-STACK (v0.2 adds the trust tasks) and consolidates the
validated planning, grounding, and now **calibration / scope-awareness** evaluation families into one
reproducible, SHA-locked suite with a baseline leaderboard.

**v0.2:** four TRUST tasks contrasting the uncertainty-aware agent with an over-confident baseline.
**T8** calibration (conformal coverage vs nominal), **T9** selective prediction (does abstaining improve
accuracy?), **T10** OOD honesty (flag extrapolation vs over-answer), **T11** out-of-scope refusal (defer
known-unknowns vs fabricate). This extends the story from "grounding separates agents" to "calibration +
scope-awareness separates *trustworthy* agents."

## Design principles

1. **Deterministic scorers.** Every task is scored by a validated function with a documented ground-truth
   source (DOI or a measured dataset). No human/LLM judging.
2. **No circular labels.** The Phase-3 targeted-intent recovery@k was *definitional* (an
   on-target identity term ranks the goal's own gene first by construction). It is **excluded**. The site
   task uses the de-circularized **blind safe-harbour discovery** (16 GSH loci vs matched controls; AUROC reported with its CI and N).
   See `docs/benchmark_circularity.md`.
3. **No fabrication is a hard gate.** An agent solver may reach the planner's numbers *only* by grounding
   every value in a tool result. Any invented number fails task `T6` and is disqualified.
4. **Scope.** Tasks are bounded by the available documented writes (small, survivorship-biased). The
   bench measures grounded planning quality and site/writer/off-target discrimination, **not** clinical
   outcome.

## Task taxonomy

| Family | Task | Scorer | Ground truth |
|---|---|---|---|
| T1 site selection | `site_selection_blind_gsh` | blind GSH discovery AUROC (+ bootstrap CI) | 16 GSH loci (8 validated) vs matched controls |
| T2 writer selection | `writer_family_recovery` | writer recovery@1 vs prevalence | 8 DOI writes, 4 families |
| T3 within-locus | `within_locus_ranking` | fraction in top quartile | documented integration bins |
| T4 off-target | `bridge_offtarget_discrimination` | model vs Hamming AUROC | Perry et al. 2025 measured off-targets |
| T5 intent | `intent_specification_compliance` | specification-correct cases | edit-intent table |
| T6 no-fabrication | `agent_no_fabrication` | **hard gate**: 0 fabricated numbers | agent trace equals direct tool calls |
| T7 ungrounded contrast | `ungrounded_llm_contrast` | fabrication rate of the same models with no tools | cached LLM transcripts |
| **T8 calibration** | `calibration_coverage` | conformal coverage vs nominal (vs uncalibrated) | held-out TRIP (N=11,433) |
| **T9 selective prediction** | `selective_prediction_usefulness` | accuracy of high-conf decile vs no abstention | held-out TRIP risk-coverage |
| **T10 OOD honesty** | `ood_honesty` | OOD flag rate (vs over-confident never-flags) | constructed OOD set (deterministic) |
| **T11 out-of-scope** | `out_of_scope_refusal` | deferral rate (vs ungrounded no-scope) | known-unknowns registry |

## Solvers

- **deterministic_planner**: the validated PEN-STACK planning tools (the reference).
- **naive_baseline**: the baseline inside each scorer (safety-only, prevalence, Hamming).
- **llm_agent (PEN-Agent)**: `agent/orchestrator.py` plus the grounded state machine `agent/pen_agent.py`,
  driven through the MCP tool registry. On grounded tasks its numbers *equal* the planner's, because it
  orchestrates the same tools; its distinguishing axis is passing the no-fabrication gate.

## Run it

```bash
python bench/run.py            # all tasks -> out/bench_results.json + LEADERBOARD.md
python bench/run.py --agent    # also run the PEN-Agent no-fabrication solver
python bench/run.py --verify   # check the frozen reference SHA256SUMS
```

Tasks that need the Phase-1 writability atlas (Zenodo), the copyrighted Perry 2025 tables (local), or an LLM
server report `available: false` when those are absent, so the command runs on any machine and fully on the
VM/local. The frozen reference inputs are SHA-locked in `SHA256SUMS`.

## External LLM-agent baseline (verified)

The `llm_agent` row is the **real LLM orchestrator** (`agent/orchestrator.py`) driving the validated tools,
audited so every number in its trace equals a direct tool call (no fabrication). Verified on the production
VM (RTX A4000, local Ollama `qwen2.5:7b-instruct`):

```
provider: ollama   llm_driven: True   grounded tool calls: >=1   no_fabrication: True
```

i.e. the LLM reaches the deterministic planner's numbers **only by grounding every value**, and is
disqualified if it fabricates. On a machine without a fast local model (e.g. the dev laptop using the slow
hosted fallback) the orchestrator may gracefully fall back to the grounded tools mid-run; the leaderboard
note states how many goals were LLM-driven vs fell back, and the no-fabrication result holds either
way. Run it yourself with `python bench/run.py --agent` (or `docker compose run --rm bench python bench/run.py --agent`).

## Leaderboard

See [`LEADERBOARD.md`](./LEADERBOARD.md) (regenerated by `bench/run.py`). Submissions: add a solver that
implements the task interface and open a PR with its `bench_results.json`; the no-fabrication gate (T6) is
mandatory for any agent solver.
