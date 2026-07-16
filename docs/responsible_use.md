# Responsible use & the safety gate (v5.7, "the Guardian")

PEN-STACK is built to help legitimate genome-writing science: gene therapy, cell engineering, synthetic
biology. From v5.7 onward, **every design submitted to `verify()` first passes a biosecurity / dual-use
screening gate**. This page states what that gate does, what it does not, and the responsibilities it assumes.

## What the gate is

A defensive screen that flags designs matching **controlled-hazard signatures** (select agents, pandemic-
potential pathogens, and controlled toxins) at the **function / family / taxon level**, and turns each result
into a logged decision:

| Decision | When | Effect |
|---|---|---|
| **clear** | no hazard signal | proceeds normally |
| **flag** | low-severity advisory | proceeds with a recorded note |
| **escalate** | ambiguous dual-use (e.g. gain-of-function) | routed to **human review** (e.g. HHS P3CO / DURC / IBC) |
| **refuse** | high-severity hazard signature | the design is **not evaluated, scored, generated, or exported** |

The gate is **orthogonal** to the immune-risk profile (v5.1, v5.6): that asks *"will the patient react to this
therapeutic vector?"*; the Guardian asks *"is this design itself hazardous / dual-use?"*. Both attach to every
`Verdict`, and neither replaces the other.

## How it catches what homology alone misses

Three+ screens run on the **design artifact** (declared function tags / Pfam domains / source taxon /
delivery / sub-designs):

- **function screen**: flags controlled-toxin and pathogen-essential **functions**. This is what catches an
  **AI-designed homolog**: a low-identity sequence still carries a hazardous *function*, and function, not
  sequence similarity, is the load-bearing axis.
- **taxon screen**: flags regulated-pathogen taxa (Select Agent / Australia Group membership).
- **chimera screen**: flags hazardous **assembly of individually-benign parts** (a toxin payload + broad
  systemic delivery; a virulence function in a replication-competent vector; a hazard split across a multiplex
  plan to evade a per-design screen).
- **sequence-homology screen**: delegated to a wrappable external screener (IBBIS Common Mechanism /
  SecureDNA-style); the in-repo baseline is a no-op (a safeguard, not a guarantee).

**The artifact decides, not the framing.** Free-text justification ("for defensive research only") is stripped
before screening, so re-framing a hazardous design cannot flip a refusal to a pass.

## Refusal & escalation taxonomy

Decisions are governed by the highest-severity hit and the version-pinned policy
(`configs/safety/policy.yaml`). Conservative by design: ambiguous dual-use **escalates** to human review rather
than silently passing or blanket-refusing. Gain-of-function / enhanced-transmissibility escalates (there is a
legitimate human-oversight pathway, HHS P3CO / DURC), and a regulated *taxon* dominates to refuse.

## Accountability: the audit trail

Every decision is appended to a **tamper-evident, hash-chained audit log** (`out/safety_audit.log`, path
overridable via `PEN_STACK_SAFETY_AUDIT`). The log stores a design **digest** (sha256), not the design. It is
an accountability record, not a hazard store. `pen_stack.safety.verify_chain()` detects any altered record.

## Scope and limitations

- Screening **reduces, does not eliminate** dual-use risk. Signatures evolve and are versioned
  (`configs/safety/hazard_registry.yaml`, `registry_version`).
- The registry holds **function / family / taxon-level signatures only**: no hazard sequences, no synthesis or
  enhancement detail (exploit detail is intentionally not published).
- The gate is **not a substitute for institutional biosafety / IBC review**, and `escalate` assumes a human
  reviewer is in the loop.
- All Pfam accessions are independently verified against EBI InterPro before reliance (one error, PF01375, was
  caught and corrected).

## For integrators

```python
from pen_stack.verify import verify
v = verify(design, actor="lab-alice")          # safety gate runs first; refused designs short-circuit
v.safety.decision                                # "clear" | "flag" | "escalate" | "refuse"
v.safety.reason                                  # the named reason

from pen_stack.safety import safety_gate, verify_chain
safety_gate(design, actor="lab-alice")           # the gate directly
verify_chain()                                    # audit integrity check
```

### Sequence screening (v7.3.12)

`safety_gate`'s default registry (`HazardRegistry.default()`) already wires a **local Pfam/HMMER domain
screen** (`pen_stack/safety/pfam_scan.py`) as its `external_hook`: a raw `cargo_seq`/`cargo_sequence` (DNA,
RNA, or protein) is 6-frame-translated as needed and scored against bundled public Pfam profile HMMs for the
SAME curated toxin families in `configs/safety/hazard_registry.yaml`, using each profile's own Pfam
gathering (GA) cutoff. No hazard sequences are bundled, profile HMMs are statistical family models built
from many aligned public sequences, not any one organism's sequence.

**Scope**: this catches a hazardous sequence for one of the ~17 curated families even with no declared
`cargo_function`, but it is still limited to that curated list, same as the function screen. It is **not**
a substitute for a full external homology screener (e.g. IBBIS Common Mechanism / SecureDNA) over a much
larger reference set. To wrap one of those instead (or in addition):

```python
from pen_stack.safety.registry import HazardRegistry
reg = HazardRegistry.load(external_hook=my_common_mechanism_screen)   # overrides the local Pfam/HMMER default
```
