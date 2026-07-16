# The genome-writing rule base (`configs/rules/*.yaml`), v3.3

The *laws of genome writing* are versioned data, not code. Each rule is one record with an `id`, a `kind`
(`hard_reject` | `soft_penalty` | `scope_flag`), the `mechanism` it encodes, a controlling `param`, a
`provenance` (DOI), a `test_ref`, and the registered `evaluator` that executes it by delegating to the
existing validated function, so relocation changes no decision (confirmed by a parity test).

| Category | Rules | Kind(s) | Source code it delegates to |
|---|---|---|---|
| reachability | `reachability.target_element_available` | hard_reject | `planner/target_site.py` (+ `configs/target_sites.yaml`) |
| fold | `fold.cross_loop_complementarity` | soft_penalty | `bridge/fold_qc.py` |
| payload | `payload.cargo_within_capacity`, `payload.split_aav_efficiency` | hard_reject, soft_penalty | `configs/delivery_vehicles.yaml` |
| multiplex | `multiplex.translocation_risk` | soft_penalty | `planner/multiplex.py` |
| delivery | `delivery.cargo_form_compatible`, `delivery.no_integration_constraint`, `delivery.sequence_constraints`, `delivery.immunogenicity_magnitude` | hard_reject ×2, soft_penalty, scope_flag | `planner/delivery_vehicles.py` + `delivery_constraints.py` |

**Legality = every applicable hard_reject rule passes.** Soft penalties flag but do not block; scope flags
declare an out-of-scope dimension (e.g. immunogenicity magnitude), never a hard reject dressed as physics.
Add a rule by adding a YAML record (+ an evaluator if new); never scatter `if` checks in the planner.
Query: `from pen_stack.rules import load_ruleset, legality_report, Design`.
