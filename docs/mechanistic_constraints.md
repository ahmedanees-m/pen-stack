# Mechanistic constraints in PEN-STACK (v3.2)

The funnel rejects ideas the physics rules out. v3.2 extends the computable filters **only where the mechanism
is genuinely computable**; the unknown parts of the funnel stay out of scope ([`scope.md`](scope.md)). Every
constraint is either a **hard physical reject** (sequence-computable) or a **labeled soft penalty** (validated
directionally). Nothing is added for the unknown parts.

## Target-site / PAM / att-site availability: a hard reject ([`pen_stack/planner/target_site.py`](../pen_stack/planner/target_site.py))

For each writer family, does the candidate site sequence carry the targeting element its mechanism *requires*?
No usable element → the writer is physically unreachable there and is **rejected**. Definitions in
[`configs/target_sites.yaml`](../configs/target_sites.yaml):

| Family | Requirement | Reject when… |
|---|---|---|
| Cas9 / Cas12a | a PAM (NGG / TTTV) in the window | no PAM present |
| CAST (Cas12k) | a GTN PAM (+ a fixed +60-66 bp insertion offset) | no PAM present |
| bridge / seek (IS110/IS1111) | the central core dinucleotide (CT); loops are reprogrammable | no core present |
| serine integrase (Bxb1) | an attB/attP (pseudo-)att site | **no att: needs a pre-installed landing pad** (the key reject) |
| PE-integrase (PASTE) | PE installs its own att beacon | broadly reachable (no native motif) |

**Validation (`validate/target_site_controls.py`):** positive controls (a site carrying the element →
available) and negative controls (a motif-absent site → reject) both pass 9/9. The key result is the *negative*:
a physically impossible writer-site pairing is rejected. These are **screens** (especially approximate for
relaxed-PAM engineered variants), not activity guarantees.

## Delivery-vehicle sequence constraints: soft penalties ([`pen_stack/planner/delivery_constraints.py`](../pen_stack/planner/delivery_constraints.py))

Vehicle-specific construct problems, as soft penalties with a concrete fix each
([`configs/delivery_constraints.yaml`](../configs/delivery_constraints.yaml)): lentiviral internal poly(A)
signals (truncate the genomic RNA), AAV ITR-interfering inverted repeats / homopolymer slippage, recombinogenic
direct repeats, packaging-hostile GC extremes. RNA-delivered vehicles (mRNA-RNP, LNP) carry no DNA-vector
packaging checks on the cargo. Directional (a construct with a known problematic element scores higher than a
clean one); a labeled heuristic, not a titre predictor. Wired into `recommend_delivery(..., cargo_seq=...)`.

## Off-target energetics: the one model that earned its place ([`pen_stack/bridge/offtarget_energetics.py`](../pen_stack/bridge/offtarget_energetics.py))

The position-weight ranker ignores *which* substitution a mismatch is; a bridge-RNA:target duplex is
base-pairing, so the thermodynamic cost depends on the substitution identity, not only its position. The
energetics model learns a per-(position, substitution) penalty from the measured off-target frequencies, a
log-additive binding-energy proxy.

**Gate: ship only if it beats the 0.77 held-out baseline.** Leakage-safe: penalties fit on a TRAIN
split, AUROC on a HELD-OUT split. On the **core_disrupted** construction (decoy flips the core; the *same*
construction the published 0.77 uses) energetics scores **0.88 vs 0.77** (robust across 5 seeds) → it ships
as the default ranker (`bridge/offtarget.py::site_risk`) via a committed penalty table, falling back to
position-weight when absent.

*What the gain actually is (precise claim, after a reviewer-driven re-run).* The 0.88-vs-0.77 gap is **mostly
the core-penalisation artifact**: in `core_disrupted`, positive and decoy differ only at the conserved core,
and because training positives are core-preserved the energetics core penalty grows ~unboundedly with N (the
position-weight model is capped). When the core is **held matched** and decoys differ only at a **non-core**
position (`core_preserved`, n≈3,056), both models collapse to ~0.65-0.69 and the gap shrinks to **Δ≈0.04**
(energetics 0.687 vs position-weight 0.646, stable across seeds). So substitution identity at non-core
positions carries a **real but modest** signal (~0.04), not the larger ~0.115. **Caveat (equally true of the
original 0.77):** both AUROCs use a favourable negative set, decoys derived from real off-targets, since
Perry S2 observes only recombined sites. Reported precisely under `by_negative_construction` in
`validate/offtarget_energetics_eval.py`. This is the only place v3.2 adds mechanism to a model rather than
wrapping it; it earns its place on the comparable construction, with the non-core gain stated plainly.
