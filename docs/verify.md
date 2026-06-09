# The PEN-STACK Verifier (`verify(design) → Verdict`) — v3.3

PEN-STACK is a **type checker for genome writes**. Submit a proposed write; get back whether it is *physically
legal*, the named reason for any rejection, a *calibrated confidence* on the soft components, an epistemic
status, and any *out-of-scope* flags. Callable as a Python function, a REST endpoint, and an MCP tool.

## Legality ≠ confidence (the contract)

Two **distinct** axes, never collapsed:
- **`legal`** — does the design pass every applicable **hard** rule (reachability, payload, delivery
  compatibility)? Deterministic, rule-based, always grounded. `True` / `False` / `None` (deferred).
- **`confidence`** — calibrated trust in the **soft/learned** components (the v3.2 L4 layer), with an
  interval. `None` when not groundable (the verifier abstains rather than guess).

A design can be **legal-but-low-confidence** or **illegal-with-certainty**. The `Verdict` carries both.

## Request

```python
from pen_stack.verify import verify
verdict = verify({
  "write_type": "insertion",          # insertion | excision | inversion | replacement |
                                       # regulatory_rewrite | landing_pad_install | multiplex
  "writer_family": "bridge_IS110",    # bridge/seek/CAST_VK/serine_integrase/PE_integrase/Cas9/Cas12a
  "site_seq": "ACGT...",              # sequence window at the target (reachability check)
  "cargo_bp": 3000,
  "delivery_vehicle": "AAV_single",   # see configs/delivery_vehicles.yaml (8 vehicles)
  "cell_type": "k562", "edit_intent": "safe_harbour_insertion",
  "no_integration": false,
  # optional soft-confidence inputs: safety, p_durable, writer_activity
  # optional: target_guide / donor_guide (fold), edits=[...] (multiplex), question="..." (scope check)
})
```

REST: `POST /verify` with the same JSON body. MCP: tool `verify_write(design: dict)`.

## Response (`Verdict`)

```json
{
  "legal": false, "deferred": false, "write_type": "insertion",
  "routing": {"rule_categories": ["reachability","fold","payload","delivery"], "steps": [...]},
  "violations": [{"rule_id": "payload.cargo_within_capacity",
                  "reason": "cargo 35000 bp exceeds AAV_single capacity 4700 bp",
                  "citation": ["10.1038/s41573-019-0012-9"]}],
  "soft_flags": [...], "scope_flags": [{"kind":"rule_scope","rule_id":"delivery.immunogenicity_magnitude", ...}],
  "confidence": null, "interval": null, "epistemic_status": "grounded-confident",
  "provenance": {"rules_version": "1.0", "source": "rules.solver + L4(...)"}, "no_fabrication": true
}
```

## Guarantees

- **No fabrication.** Every number traces to a tool: legality is rule-deterministic, confidence is the
  calibrated L4 value, rule values come from the validated functions. `no_fabrication: true` always.
- **Named, cited reasons.** Each hard-rule rejection carries its `rule_id`, a human reason, and a DOI.
- **Deferral, not guessing.** Unsupported write types defer (`legal: null`); out-of-scope questions
  (known-unknowns) are flagged, never answered.
- **Rules are data.** See `configs/rules/*.yaml` (`docs/rules.md`) and `configs/delivery_vehicles.yaml`
  (`docs/delivery.md`).
