# Chat Routing Benchmark

Measures whether the deterministic four-lane router (`pen_stack.web.router.classify`) sends each query to the right
lane - and, the **safety-critical** property, that a write/result request **never leaks to the ungrounded General
lane**. Deterministic (no LLM/embedder); fully reproducible in CI.

## Lanes
`design` (engine, guard on) · `explain` (metric guide) · `meta` (live capability facts) · `general` (retrieval-grounded).

## Sealed set
`cases.jsonl` - 40 labelled queries across the four lanes, including back-reference follow-ups (with a synthetic
grounded prior) and ambiguous phrasings. SHA-locked in `SHA256SUMS`.

## Metrics + gate
- per-lane precision / recall / F1 + the confusion matrix;
- **`routing_safety_metric` = P(a `design`/write request routes to `general`)** - the dangerous failure; **target ~0**;
- `grounded_to_general_leaks` = any grounded-lane gold that routed to `general`.

## Result (committed, `result.json`)
| metric | value |
|---|---|
| accuracy | **1.000** (40/40) |
| routing_safety_metric | **0.000** (no write request leaks to general) |
| grounded -> general leaks | **0** |
| min per-lane F1 | **1.000** |
| safety gate (safety ~0) | **pass** |

The router is deliberately conservative: **an action verb plus any one target signal routes to the grounded
design lane**. A stricter rule requiring two signals even with an action verb leaks 3 of 11 write requests to
`general` (`routing_safety_metric = 0.273`), because the `cell`/`locus` regexes then miss plurals like
*hepatocytes*, *HSPCs*, *iPSCs*. The conservative rule is the shipped one, per the pre-specified discipline
(*tighten, never relax the metric*). Over-routing a borderline question to a grounded lane is the safe failure
direction; under-routing a real request to `general` is the dangerous one.

Reproduce: `python -c "from benchmarks.chat_routing.harness import run; print(run())"`.
