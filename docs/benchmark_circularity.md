# The circularity in the Phase-3 recovery@k benchmark (and how v3.1 fixes it)

**Status:** acknowledged defect. This document is WS-A1 of the v3.1 cycle. A second reader should be able to
reproduce the argument from this document and the code alone.

## The defect

The Phase-3 "two-stratum recovery@k benchmark" (`pen_stack/validate/paper3_benchmark.py`) reported a
headline of **discriminating-stratum recovery@10 = 1.00 vs 0.00** for an intent-blind baseline, with a
McNemar p = 0.0156 and a bootstrap CI excluding zero. For the **discriminating (targeted) intents**
(`knock_in_with_disruption`, `high_durability_insertion`, `regulatory_excision`, `repeat_excision`) **this
result is circular and must not be presented as predictive evidence.**

The mechanism:

1. The benchmark marks a candidate as on-target by **identity with the goal's gene**:
   `pool["on_target"] = (pool["gene"] == t["gene"]) & (not genome_wide)`
   (`paper3_benchmark.py`, in `recovery_at_k`).
2. The optimiser adds an on-target term scaled by `on_target_magnitude: 1.0`
   (`configs/intent_weights.yaml`), with a `target_gene_sign` of `-1` for the targeted intents (i.e. the
   term is a **reward**). See `pen_stack/planner/optimize.py::score_candidates`:
   `out["score"] = base - target_gene_sign * mag * on_target`.
3. The base score is a convex combination of `safety`, `p_durable`, and `writer_activity`, each in `[0, 1]`
   with weights summing to ~1, so the base lies in `[0, 1]`. Adding `+1.0` for the on-target candidate
   therefore **dominates** every off-target candidate's score by construction.

Consequently, for a targeted intent the planner ranks **the goal's own gene first by definition**, and the
benchmark's "recovery" of that gene is **near-definitional, not a prediction**. Attaching a McNemar test
and a confidence interval to a definitional outcome dresses a tautology as evidence. The intent-blind
baseline "fails" only because it was deliberately denied the goal - that contrast is real and useful as a
*specification* statement, but it is not a measure of predictive skill.

## What is NOT circular

The **control stratum** (safe-harbour intents) runs with `genome_wide = True`, so `on_target` never fires
and the planner ranks the candidate pool purely by `safety x durability x activity`. That is a genuine
search, not a confirmation. The non-circular signal therefore already lived in the control stratum; v3.1
promotes it to the headline and strengthens it.

## The fix (WS-A)

- **A2 - reframe intent-sensitivity as specification-compliance.** Keep the demonstration that the same
  locus changes rank under opposing goals, but report it as a behavioral-correctness table
  (`pen_stack/validate/intent_specification.py`). Remove all "recovery@k", p-value, and CI language for
  the targeted-intent gene-level result, everywhere (code, docstrings, README, manuscript).
- **A3 - blind safe-harbour site discovery (the new headline).** Hold out literature-validated safe
  harbours, run the planner genome-wide (so on-target cannot fire), and test whether the held-out GSH bins
  rank above **matched-context random controls** (matched on chromatin state, gene density, distance-to-TSS
  bucket). Report AUROC and recovery@k. This is a search, not a confirmation
  (`pen_stack/validate/blind_gsh_discovery.py`).
- **A4 - diversified writer recovery.** Add DSB-free large-cargo documented writes so the correct writer
  family genuinely varies with cargo size; recover the family from goal + intent + cargo + cell type with
  the writer held out (`pen_stack/validate/writer_recovery.py`).
- **A5 - within-locus ranking.** Within a large safe-harbour gene, test whether the documented intronic
  safe bin ranks above other bins in the locus (`pen_stack/validate/within_locus_ranking.py`).
- **A6 - consolidated report** with a scope statement per task; the **headline is the blind result**, not
  the targeted-intent recovery.

## Acceptance for A1

A second reader, given this document plus `paper3_benchmark.py`, `intent_weights.yaml`, and `optimize.py`,
can independently reproduce: (i) where on-target identity is set, (ii) where the magnitude-1.0 reward is
applied, (iii) why it dominates a `[0,1]` base, and therefore (iv) why targeted-intent gene-level recovery
is definitional. No tuning is required to see it; it follows from the configuration.
