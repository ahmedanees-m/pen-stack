# The build interface (v5.11)

From v5.11, PEN-STACK reaches the **digital→physical** interface, responsibly. A cleared, legal design becomes a
runnable protocol DRAFT carrying its v5.6 immune-risk profile (refused outright if the v5.7 safety gate flags it);
a typed ingestion API returns experimental results as candidate evidence admitted only through the v4.5
world-model gate; and a simulated lab runs the whole loop before any hardware exists. PEN-STACK **emits protocols
and ingests results; it does not run experiments.**

## Safety-gated protocol export (`pen_stack/build/protocol.py`)

```python
from pen_stack.build import export_protocol, ProtocolExportError
code = export_protocol(design, {"round": 0}, target="opentrons", actor="lab-alice")
```

`export_protocol` runs `verify(design, actor)` **first**. If the safety gate returns `refuse`, or the design is
illegal, it raises **`ProtocolExportError`**: there is no export path for a flagged design. A cleared design is
emitted for one of `opentrons` / `pylabrobot` / `cloudlab`, **stamped "DRAFT, human/lab review required"**, with
the v5.6 immune profile and full provenance in the metadata. Protocols are drafts; nothing is auto-run.

## Typed, gated ingestion (`pen_stack/build/ingest.py`)

```python
from pen_stack.build import ingest_result
cand = ingest_result(result)                       # quarantined measured Candidate (no auto-merge)
ingest_result(result, admitted_by="human", graph=g, approved=True)   # the ONLY path into the curated graph
```

A result is validated (assay / readout / provenance with a source) and turned into a **quarantined measured edge
Candidate**. The only way it enters the curated world-model is the v4.5 gate (`gate_admit`): automated checks
**and** explicit human approval. No process auto-edits curated truth (Principle 1). Immune-measurement results can
begin validating the v5.6 proxies on a later pass.

## Simulated lab (`pen_stack/build/simlab.py`)

```python
from pen_stack.build import run_simulated
res = run_simulated(protocol_ir, design, cell_state="k562", seed=0)
```

`run_simulated` executes a protocol in silico: it samples an "observed" readout from the v5.9 twin + measurement
noise, **labelled `SIMULATED`**. This lets the closed loop (v5.12) run end-to-end **export → sim → ingest** without
a wet lab. Sim outcomes inherit the twin's limits and **never** enter the curated world-model as measured truth.

## Scope

PEN-STACK emits protocols and ingests results; it does **not** run experiments. Protocols are drafts requiring
human/lab review, results enter only through the gate, and the simulated lab is for development and loop-validation,
never a substitute for real data. Export is hard-blocked for anything the safety gate flags; the attached immune
profile is a screen carrying its known-unknowns, not a patient prediction.
