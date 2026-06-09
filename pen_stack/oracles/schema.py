"""The oracle contract — one uniform result type for every foundation model (v4.0, WS-O).

v4.0 makes PEN-STACK the composition + verification layer *on top of* the biomolecular foundation models
(AlphaGenome, Evo2, AlphaFold3, Boltz-2, Chai-1, Protenix, ESM3, RFdiffusion, ProteinMPNN, ViennaRNA, ...).
Every oracle, however different internally, answers through ONE contract:

    predict(...) -> OracleResult{value, provenance(model+version), native_uncertainty, scope}

Three invariants are encoded in the type itself (v4.0 principles):
  1. **A generative output is a candidate, never a claim** — `candidate=True` outputs cannot enter a claim
     path without passing writer-verification (`as_claim()` raises; a guard test asserts it).
  2. **One contract for every oracle** — provenance (model+version) and the oracle's *native* uncertainty are
     always carried, never discarded; every call is cache-keyed on inputs+model+version.
  3. **Scope is explicit** — each result carries the id of its oracle's scope card and an `extrapolating`
     flag; the field's evidence that these models do not generalize to unseen loci is *labelled*, not hidden.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

OutputKind = Literal["claim", "candidate", "baseline"]


class Provenance(BaseModel):
    model: str                                  # e.g. "boltz-2", "alphagenome", "evo2"
    version: str                                # pinned model/version string
    source: str = "adapter"                     # adapter | cache | hosted_api | local_gpu
    cache_key: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class OracleResult(BaseModel):
    """The single result type returned by every oracle adapter."""
    oracle: str                                 # family: genome | structure | protein_design | rna | energetics
    value: Any | None                           # the prediction (kind depends on the oracle)
    provenance: Provenance
    native_uncertainty: float | None = None     # the oracle's OWN uncertainty (e.g. 1 - pLDDT), surfaced not hidden
    scope_card: str | None = None               # id of the scope card stating what this oracle is valid for
    in_scope: bool = True                       # input falls within the scope card
    extrapolating: bool = False                 # OOD relative to the oracle's training/validity envelope
    output_kind: OutputKind = "claim"           # claim | candidate (generative) | baseline (honest comparator)
    available: bool = True                      # backend present + ran (False -> deferred, value may be cached/None)
    cached: bool = False
    note: str | None = None

    @property
    def is_candidate(self) -> bool:
        return self.output_kind == "candidate"

    def as_claim(self) -> "OracleResult":
        """Return self for use in a claim path, or RAISE if this is a generative candidate (Principle 1).

        A generated sequence/structure/backbone (Evo2/ESM3/RFdiffusion/ProteinMPNN) is a *proposal*; it must be
        scored against measured data through writer-verification (WS-WV) before any claim. This guard makes the
        pen-assemble lesson (0 validatable de-novo writers) un-bypassable in code."""
        if self.is_candidate:
            raise ValueError(
                f"oracle '{self.provenance.model}' returned a CANDIDATE ({self.oracle}); it cannot enter a "
                "claim path without writer-verification scoring (v4.0 Principle 1). Call "
                "pen_stack.atlas.writer_verify on it first.")
        return self
