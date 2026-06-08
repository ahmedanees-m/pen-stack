# PEN-STACK — Scope and the edge of what it knows (v3.2)

PEN-STACK is a *trustworthy* co-scientist because it is **legible about the edge of its own knowledge**, not
because it pretends to model everything. This page is that edge, made explicit. It complements the calibrated
uncertainty (conformal intervals + OOD, see [`uncertainty.md`](uncertainty.md)) with an explicit list of what
is **out of scope** — biology beyond any tool here.

## Three epistemic statuses

Every agent output carries exactly one status, driven by the WS-UQ signals (never hand-set):

| Status | Meaning |
|---|---|
| **grounded-confident** | tool-grounded, in-distribution (low OOD), calibrated, above the abstention threshold |
| **grounded-extrapolating** | tool-grounded but the OOD detector flags the query as far from training data, or the conformal interval is wide / confidence low — the number is real but the model is extrapolating |
| **not-computable** | no validated tool can ground it: the step refused, the query is out of scope (a known-unknown), or the agent abstained — the honest "I don't know" |

Implemented in [`pen_stack/agent/epistemic.py`](../pen_stack/agent/epistemic.py).

## What PEN-STACK does NOT model (the known-unknowns registry)

The unknown parts of the funnel stay **explicitly out of scope** — surfaced, not faked. The scope matcher
([`pen_stack/agent/scope.py`](../pen_stack/agent/scope.py)) matches an incoming question against
[`configs/known_unknowns.yaml`](../configs/known_unknowns.yaml) and defers rather than guessing:

| Known-unknown | Why it is out of scope |
|---|---|
| **structure → phenotype** | the structure→function→phenotype map is an open problem; no tool predicts organismal phenotype from a structural/sequence edit |
| **in-vivo immunogenicity** | PEN-STACK scores deliverability + sequence-level heuristics, not a patient's in-vivo immune response to a writer/capsid |
| **long-term clinical durability** | the durability model is a *conditional chromatin-context* model (position effect on an integrated cassette), not multi-year in-vivo persistence/clonal dynamics |
| **higher-order epistasis** | the multiplex module screens *pairwise* translocation risk only, not functional epistasis among 3+ edits |
| **polygenic effects** | PEN-STACK is single-locus / per-write, not polygenic trait architecture |
| **germline / heritable** | PEN-STACK is a somatic design tool; it does not model germline transmission and takes no position on germline editing |

This boundary is made *legible* by v3.2 — it is **not closed**. No amount of feeding equations closes it, for
anyone, today. As validated gold sets grow, the *calibrated* region widens; the out-of-scope list stays the
honest statement of what no tool here can ground.

## Distinct from the clinical-directive refusal

The scope matcher (out-of-scope *biology*) complements the clinical-directive refusal in
[`pen_stack/agent/guardrails.py`](../pen_stack/agent/guardrails.py) (out-of-scope *advice*: "should I dose my
patient…"). Both end at the same place — a deferral with zero fabrication — but for different reasons.

## Acceptance

[`pen_stack/validate/out_of_scope_refusal.py`](../pen_stack/validate/out_of_scope_refusal.py): the scope
matcher defers **100%** of curated out-of-scope probes and **0%** of curated in-scope genome-writing
questions (no over-refusal). An ungrounded model with no scope layer answers the out-of-scope probes with a
concrete value — exactly the fabrication the scope layer prevents.
