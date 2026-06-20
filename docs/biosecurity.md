# The Guardian: biosecurity screening internals (v5.7)

Technical reference for `pen_stack/safety/`. For the policy framing and integrator quickstart see
[Responsible use](responsible_use.md). (Distinct from the genotoxicity **safety layer** model card under
`cards/safety.md`, which scores a *locus*; this screens a *design* for dual-use hazard.)

## Modules

| Module | Role |
|---|---|
| `safety/registry.py` | `HazardRegistry`: loads version-pinned signatures from `configs/safety/hazard_registry.yaml`; the screen methods (`function_flags`, `taxon_flags`, `chimera_context`, `sequence_homology`). |
| `safety/screen.py` | `ScreenHit` (typed, provenanced) + `screen_design(design)` orchestrating all screens. |
| `safety/policy.py` | `SafetyVerdict` + `decide(hits)` (severity → decision) from `configs/safety/policy.yaml`. |
| `safety/gate.py` | `safety_gate(design, actor=…)` = strip-framing → screen → decide → audit. |
| `safety/audit.py` | append-only hash-chained `audit_log` + `verify_chain`. |
| `safety/redteam.py` | `run_red_team()` adversarial harness. |

## The registry (curated, versioned, public-reference-only)

`configs/safety/hazard_registry.yaml` (`registry_version`) holds four sections, all at the
function/family/taxon level with **public Pfam accessions and public control-list references**, and **no**
hazard sequences or operational detail:

- `toxin_functions`: controlled toxins by Pfam (e.g. ricin/RIP `PF00161`+`PF00652`; botulinum `PF01742`
  +`PF07951/2/3`; diphtheria `PF01324`/`PF02763`; anthrax LF `PF03497` + PA `PF03495`/`PF20835`/`PF17475`
  /`PF17476`; staph/strep `PF01123`/`PF02876`; conotoxin `PF02950`; cholera/heat-labile enterotoxin `PF01375`)
  plus matching `keywords`.
- `regulated_taxa`: Select Agent / Australia Group pathogens by name + `aliases` (Variola, reconstructed 1918
  influenza, Ebola/Marburg, Nipah/Hendra, SARS/MERS, Yersinia pestis).
- `controlled_functions`: dual-use functions (enhanced transmissibility → escalate; immune evasion;
  pathogen-essential virulence).
- `chimera_rules`: toxin+broad-delivery; virulence+replication; split-hazard.

> **All Pfam accessions are independently verified against EBI InterPro before reliance.** One error (PF01375,
> originally mislabeled anthrax; it is heat-labile/cholera enterotoxin) was caught and corrected; anthrax PA
> was re-sourced from the authoritative PA protein record (UniProt P13423). See
> `phase_5.7/DATA_ID_VERIFICATION_v5.7-v5.13.md`.

## Decision flow

```
design ──strip framing──▶ screen_design ──▶ [ScreenHit, …] ──decide──▶ SafetyVerdict ──audit_log──▶ chained record
                          (function/taxon/                (highest      (clear/flag/
                           chimera/seq-homology)           severity)     escalate/refuse)
```

`verify()` runs the gate first; a `refuse` short-circuits (the design is returned un-evaluated with a
`safety_refused` scope flag); otherwise the `SafetyVerdict` is attached to the `Verdict`.

## Extending it

- **Add a signature:** add an entry (with `pfam`/`keywords`/`severity`/`control_ref`) to the registry and bump
  `registry_version`; add a probe to `configs/safety/probes.yaml` and re-SHA-lock.
- **Wrap an external screener:** `HazardRegistry.load(external_hook=fn)` enables the sequence-homology path
  (e.g. IBBIS Common Mechanism / SecureDNA), returning `ScreenHit`s of kind `sequence_homology`.
- **Tune the policy:** edit `configs/safety/policy.yaml` (`severity_to_decision`, `ignore_framing_fields`).

## Pre-registered acceptance (the bench `safety_screening` task)

Benign therapeutics (FIX/FVIII/CAR-T/sickle-cell) pass with **0 false refusals**; hazard probes
(ricin/botulinum/variola/transmissibility) refused/escalated at the **correct severity**; adversarial evasions
(AI-homolog, split-hazard, reframing, chimera) **never `clear`**. The contrast is a **no-safety
baseline** that clears everything (passes benign, fails every hazard + evasion); the Guardian's
correct-decision rate (1.0) beats it (0.33) by construction. `guardian_gate_pass` is a hard gate.
