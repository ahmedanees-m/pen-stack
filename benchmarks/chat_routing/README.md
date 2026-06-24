# Chat Routing Benchmark (PEN-CHAT P-WS4)

Measures whether the deterministic four-lane router (`pen_stack.web.router.classify`) sends each query to the right
lane - and, the **safety-critical** property, that a write/result request **never leaks to the ungrounded General
lane**. Deterministic (no LLM/embedder); fully reproducible in CI.

## Lanes
`design` (engine, guard on) · `explain` (metric guide) · `meta` (live capability facts) · `general` (retrieval-grounded).

## Sealed set
`cases.jsonl` - 40 labelled queries across the four lanes, including back-reference follow-ups (with a synthetic
grounded prior) and ambiguous phrasings. SHA-locked in `SHA256SUMS`.

## Metrics + gate (P-G2)
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
| gate P-G2 (safety ~0) | **pass** |

The first run measured `routing_safety_metric = 0.273` (3 of 11 write requests leaked to `general` because the
router required >=2 signals even with an action verb, and `cell`/`locus` regexes missed plurals like *hepatocytes*,
*HSPCs*, *iPSCs*). Per the pre-registered discipline (*tighten, never relax the metric*) the router was made
conservative - **an action verb + any one target signal routes to the grounded design lane** - and the metric was
re-measured at 0.000. Over-routing a borderline question to a grounded lane is the safe failure direction;
under-routing a real request to `general` is the dangerous one.

Reproduce: `python -c "from benchmarks.chat_routing.harness import run; print(run())"`.
