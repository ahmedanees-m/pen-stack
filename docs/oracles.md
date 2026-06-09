# The oracle mesh (v4.0, WS-O)

PEN-STACK v4.0 sits **on top of** the biomolecular foundation models. `pen_stack.oracles` wraps them under one
contract so their outputs can be composed, checked by the rule-grounded verifier, and trust-calibrated —
without losing provenance, native uncertainty, or scope.

## One contract: `OracleResult`

Every adapter returns an `OracleResult`:

```
OracleResult{oracle, value, provenance{model, version, source, cache_key},
             native_uncertainty, scope_card, in_scope, extrapolating,
             output_kind ∈ {claim, candidate, baseline}, available, cached}
```

Three invariants are encoded in the type:

1. **A generative output is a candidate, never a claim.** `output_kind="candidate"` (Evo2 generation, ESM3,
   RFdiffusion, ProteinMPNN) → `as_claim()` **raises**. A candidate must pass writer-verification (WS-WV)
   before any claim. (The pen-assemble lesson — 0 validatable de-novo writers — encoded in code.)
2. **One contract for every oracle.** Provenance (model + version) and the model's *native* uncertainty are
   always carried; every call is cache-keyed on `(oracle, model, version, inputs)` and replayable offline.
3. **Scope is explicit.** Each result carries its scope-card id and an `extrapolating` flag; the field's
   evidence that these models do not generalize to unseen loci is **labelled**, not hidden.

## Wrapped models (scope cards in `configs/oracles/scope_cards.yaml`)

| Family | Models | Output kind |
|---|---|---|
| `genome` | AlphaGenome (OOD-gated), Evo2 (likelihood=claim / generation=candidate), ChromBPNet·Borzoi (baseline) | claim / candidate / baseline |
| `structure` | AlphaFold3, Boltz-2, Chai-1, Protenix + `consistency()` | claim |
| `protein_design` | ESM3, RFdiffusion(-AA), ProteinMPNN·LigandMPNN | **candidate** |
| `rna` | ViennaRNA (real; hard fold-legality input) | claim |
| `energetics` | bridge off-target (MC3 gate ≥ 0.77) | claim |

## Cross-oracle consistency

`structure.consistency(seq)` runs the available structure predictors and combines them with `consensus()`:
agreement is a confidence signal, and **disagreement widens the reported interval** (`native_uncertainty`
grows with the cross-oracle spread) — v4.0 Principle 3.

## Compute / offline policy

Heavy backends (AF3, Evo2, ESM3, …) run on-demand (hosted API / local GPU) and are cached + version-pinned
under `oracle_cache/` (committed for offline CI). When a backend and a cache entry are both absent, the
adapter returns a **deferred** result (`available=False`) — it never fabricates a value. ViennaRNA and the
bridge energetics model are real and run locally / on the VM.

See `docs/writer_verification.md` (scoring/critiquing writers through the mesh), `prereg/ws_o.yaml`, and
`pen_stack/oracles/`.
