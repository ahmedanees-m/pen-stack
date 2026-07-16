# Verification service

`verify(design)` checks a proposed genome-writing design across three separate axes and returns them without
collapsing them into one number. `verify_proof(design)` repackages the same result as a repair-oriented proof
object: an agent can read it and fix a failed design.

## The three axes

| Axis | Source | What it reports |
|---|---|---|
| Legality | the rule base (`configs/rules/*.yaml`) | every applicable hard rule passes; a failure names the violated rule and its citation |
| Confidence | the calibrated trust layer | a calibrated confidence on the soft components, or an abstention when the design is uncalibrated |
| Biosecurity | the Guardian dual-use gate | clear / flag / refuse / escalate, with the signature that fired |

The axes are reported separately and never fused: a design can be legal but low-confidence, or
high-confidence but refused on biosecurity. The collapsed verdict is always `None`.

## The proof object

`verify_proof(design)` returns a `Proof` with one `AxisProof` per axis: `{axis, status, violated, evidence,
repair_hint}`. The repair hint is actionable for legality (a structured field edit) and for the confidence
abstention (which scores to supply). `repair_from_proof(design, proof)` applies the structured repairs using
only the proof object and returns a repaired design that re-verifies; this is how a failed-on-legality design
is fixed in a loop rather than rejected.

Biosecurity repair hints are deliberately non-actionable for a hazard: a refused or escalated design is
acknowledged and routed to institutional biosafety review, never auto-repaired and never given instructions
toward the hazard.

## Published rule spec

The rule base is exported as a machine-readable, citable spec (`pen_stack/rules/spec.py::export_spec`,
committed at `benchmarks/verify/rule_spec.json`, human-readable at [docs/rule_spec.md](rule_spec.md)). A parity
check proves the exported spec round-trips to the exact ruleset the solver loads (0 mismatches), every rule
names a registered evaluator, and every rule carries a DOI or a note.

## Biosecurity standards alignment

`pen_stack/safety/standards.py` maps the Guardian's four screen kinds (function, taxon, chimera, homology) and
its four decisions onto the IBBIS Common Mechanism's reported categories and `ScreenStatus` values (Pass /
Warning / Flag), and onto SecureDNA's pass/deny outcome. `concordance_report()` runs the Guardian over a
labelled set and reports the concordance verbatim. This is a concordance, not a certification: the standard's
own tool is authoritative, and the full sequence-screening pipeline is BioFirewall.

References: IBBIS Common Mechanism (Wheeler et al. 2024, Applied Biosafety 29(2):71-78, DOI
10.1089/apb.2023.0034); SecureDNA (Baum et al., arXiv:2403.14023); US Federal Select Agents Program (42 CFR
73, 7 CFR 331, 9 CFR 121); Australia Group control lists.

## Surfaces

REST `POST /api/verify` (Verdict) and `POST /api/verify/proof` (Proof); MCP tools `verify_write` and
`verify_proof`; manifest tools `verify_write` and `verify_proof` (both `fabricates: false`).
