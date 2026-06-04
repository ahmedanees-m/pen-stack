# Genome-Writing Bench v0.1 - leaderboard submission guide

We invite submissions: deterministic planners, heuristic baselines, and LLM/agent solvers. The bench is
designed so anyone can reproduce a run and add a row.

## What a solver must do

A solver answers the six tasks (`tasks.yaml`): site selection, writer selection, within-locus ranking,
off-target discrimination, intent compliance, and no-fabrication. Each task has a **deterministic scorer**
and a **documented ground-truth source**; you do not re-implement the scorers - you provide predictions (or,
for an agent, drive the validated tools) and the harness scores them.

There are two solver classes:

1. **Tool/planner solver** - produces the ranked outputs the deterministic scorers consume. Compare against
   the reference planner and the naive baseline already on the board.
2. **Agent solver (LLM or otherwise)** - drives the validated tools through the MCP registry
   (`pen_stack.agent.mcp_server`) or the in-process orchestrator. Its numbers must come from tool calls.

## The rules (non-negotiable)

- **No-fabrication is a hard gate (T6).** Every number in an agent's trace must equal a direct tool call.
  A single invented value disqualifies the submission. This is checked automatically.
- **No circular labels.** Submissions inherit Gate G-A: no task may be scored against a definitional label
  (see `docs/benchmark_circularity.md`). The site task is blind safe-harbour discovery, not targeted-intent
  recovery.
- **Frozen reference set.** Run `python bench/run.py --verify` first; your run must be against the SHA-locked
  inputs in `SHA256SUMS`.
- **Reproducible.** Provide a one-command invocation (ideally `docker compose run --rm bench ...`) and your
  `out/bench_results.json`.

## How to submit

1. Fork the repo and add your solver (a module that implements the task interface, or an agent reachable via
   the MCP registry).
2. Run `python bench/run.py --agent` (or your solver's entrypoint) and commit the resulting
   `out/bench_results.json` and a one-line description.
3. Open a pull request titled `bench-submission: <solver name>`. Include: the solver class, the provider /
   model (for agents), the one-command invocation, and whether the no-fabrication gate passed.
4. We verify the run reproduces against the frozen SHAs and add your row to `LEADERBOARD.md`.

## Scoring and honesty

The leaderboard reports, per solver: tasks scored, whether it beats the naive baseline on grounded tasks,
the no-fabrication result, and a short note. We report **how many goals an agent was LLM-driven vs gracefully
fell back** - the no-fabrication result holds either way. We do not rank by a single composite score; the
point is to show that grounded planning beats naive baselines and that an agent can only match the planner by
grounding, never by inventing.

## Versioning

This is **v0.1**. Task definitions and frozen data are SHA-locked; any change to the reference set bumps the
bench version and is announced in `CHANGELOG.md`. Submissions are tagged with the bench version they ran on.
