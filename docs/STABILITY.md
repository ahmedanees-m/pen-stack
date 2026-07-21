# API stability & deprecation policy

PEN-STACK's public API exercised across all surfaces is
documented and frozen, with a deprecation policy. "First Stable" is **earned, not declared**; it is cut only
after the closed loop is demonstrated, the benchmark is public, and the integration surface ships.

> The first stable release is a commitment to **API stability**, not a claim of solving genetic engineering. The
> unknown funnel remains, made legible (scope flags, known-unknowns, baselines), not hidden.

## Versioning

PEN-STACK follows **semantic versioning**:

- **MAJOR** (`x.0.0`): backward-incompatible changes to the public API (below).
- **MINOR** (`0.x.0`): backward-compatible additions.
- **PATCH** (`0.0.x`): backward-compatible fixes.

## The committed public API

These are the supported entry points. Their **signatures and return-shape keys** are stable across the release series:

| Surface | Entry point |
|---|---|
| Verify a write | `pen_stack.verify.verify(design, question=None, *, actor=…) -> Verdict` (legal · safety · immune_profile · confidence · scope) |
| Safety gate | `pen_stack.safety.safety_gate(design, *, actor=…) -> SafetyVerdict` |
| Generative design | `pen_stack.design.generate_designs(...)`, `pen_stack.design.pareto_front(...)` |
| Digital twin | `pen_stack.twin.predict_outcome(design, cell_state)`, `pen_stack.twin.calibrate_outcome(...)` |
| Experiment design | `pen_stack.active.select_batch(...)`, `pen_stack.active.expected_information_gain(...)` |
| Build interface | `pen_stack.build.export_protocol(...)`, `pen_stack.build.ingest_result(...)`, `pen_stack.build.run_simulated(...)` |
| Closed loop | `pen_stack.loop.run_loop(goal, cell_state, …)` |
| Co-scientist | `pen_stack.agent.co_scientist.co_scientist_session(goal, cell_state)` |
| Challenge | `benchmarks.genome_writing_challenge.harness.evaluate(submission, round_id)` |
| CLI / MCP | `pen-stack` / `pen-bridge` console scripts; `pen_stack.agent.mcp_server` |

Internal helpers (underscore-prefixed names, modules under `pen_stack/*/_*`, the `data/`/`wgenome/` training
pipelines) are **not** part of the public API and may change in any release.

## Deprecation policy

- A public API element is deprecated by a **`DeprecationWarning`** and a release note **at least one MINOR
  release** before removal.
- Removal happens only in a **MAJOR** release.
- The `OracleResult` / `Verdict` / `SafetyVerdict` / immune-profile **contracts** (field names + invariants such as
  `collapsed_score is None` and the no-fabrication guard) are stable across the release series.

## What stability does NOT promise

- Model **numbers** may change as oracles / data are updated (they are version-pinned + provenanced; results are
  reproducible *given a pinned version*, not constant forever).
- **Scope** stays bounded: out-of-scope questions are deferred, known-unknowns declared, baselines reported, at
  every release.
