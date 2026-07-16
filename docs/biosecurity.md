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
> was re-sourced from the authoritative PA protein record (UniProt P13423).

## Decision flow

```
design ──strip framing──▶ screen_design ──▶ [ScreenHit, …] ──decide──▶ SafetyVerdict ──audit_log──▶ chained record
                          (function/taxon/                (highest      (clear/flag/
                           chimera/seq-homology)           severity)     escalate/refuse)
```

`verify()` runs the gate first; a `refuse` short-circuits (the design is returned un-evaluated with a
`safety_refused` scope flag); otherwise the `SafetyVerdict` is attached to the `Verdict`.

## Which fields are screened, and what `declared_signal` means

The gate reads hazard content **only** from these declared fields (`pen_stack/safety/gate.py`):

| Kind | Fields |
|---|---|
| Text | `cargo_function`, `function_annotation`, `goal_function`, `source_taxon`, `organism`, `host_taxon`, `cargo_seq`, `cargo_sequence` |
| List | `function_tags`, `pfam_domains`, `annotations` |

Everything else, including `edit_intent` and any other free-text or justification field, is **not** screened;
framing fields listed in `configs/safety/policy.yaml:ignore_framing_fields` are stripped *before* screening so
a hazardous design cannot be re-labelled "defensive research" to flip a `refuse` into a `clear` (the artifact
decides, not the wording).

Because of this, the verdict's `provenance.declared_signal` flag matters: **`declared_signal=False` means "no
screenable content was declared, so nothing was screened", which is NOT "screened and found safe."** A design
that put its hazard only in `edit_intent` (or submitted an empty cargo-function box) will read `clear` with
`declared_signal=False` and a reason that says so explicitly. Put hazard-relevant content in the fields above,
and treat a `clear` as meaningful only when `declared_signal=True`.

## Sequence screening (v7.3.12)

`HazardRegistry.default()`, the registry `screen_design()` uses when no explicit registry is passed, wires
`pen_stack/safety/pfam_scan.py` as its `external_hook`: a raw `cargo_seq`/`cargo_sequence` is 6-frame-
translated (DNA/RNA) or scanned directly (protein) against bundled public Pfam profile HMMs for the SAME
curated families in `toxin_functions` above, using each profile's Pfam gathering (GA) cutoff, the standard
threshold Pfam's own annotation pipeline uses to call a genuine family match. The 17 HMMs (`configs/safety/
pfam_hmms/toxin_domains.hmm`) are public statistical models built from many aligned public sequences, not any
one organism's sequence, consistent with "no hazard sequences" above. `HazardRegistry.load()` itself stays
hookless by default (bare registry, or your own hook).

Coverage is still bounded by the curated family list: this closes the "raw sequence, no declared function"
gap for those ~17 families, it is not a substitute for a full external homology screener (e.g. IBBIS Common
Mechanism / SecureDNA) over a much larger reference set.

## Extending it

- **Add a signature:** add an entry (with `pfam`/`keywords`/`severity`/`control_ref`) to the registry and bump
  `registry_version`; add a probe to `configs/safety/probes.yaml` and re-SHA-lock. If it's a new Pfam family,
  also fetch its HMM (`https://www.ebi.ac.uk/interpro/api/entry/pfam/<ACCESSION>/?annotation=hmm`) and append
  it to `configs/safety/pfam_hmms/toxin_domains.hmm` so the sequence screen covers it too.
- **Wrap a different/additional external screener:** `HazardRegistry.load(external_hook=fn)` overrides the
  local Pfam/HMMER default (e.g. IBBIS Common Mechanism / SecureDNA), returning `ScreenHit`s of kind
  `sequence_homology`.
- **Tune the policy:** edit `configs/safety/policy.yaml` (`severity_to_decision`, `ignore_framing_fields`).

## Pre-registered acceptance (the bench `safety_screening` task)

Benign therapeutics (FIX/FVIII/CAR-T/sickle-cell) pass with **0 false refusals**; hazard probes
(ricin/botulinum/variola/transmissibility) refused/escalated at the **correct severity**; adversarial evasions
(AI-homolog, split-hazard, reframing, chimera) **never `clear`**. The contrast is a **no-safety
baseline** that clears everything (passes benign, fails every hazard + evasion); the Guardian's
correct-decision rate (1.0) beats it (0.33) by construction. `guardian_gate_pass` is a hard gate.
