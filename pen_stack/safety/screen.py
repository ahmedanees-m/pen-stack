"""Sequence + function screening, the Guardian linchpin.

Runs the hazard screens over a design and returns typed, provenanced hits. Three+ screens:
  * function_flag, toxin / controlled-function domains (the screen that catches AI-homologs),
  * taxon_flag, regulated-pathogen taxon membership (Select Agent / Australia Group),
  * chimera_context, hazardous assembly of individually-benign parts,
  * sequence_homology, delegated to a wrapped external screener when enabled (baseline: no-op + a note).

Flags come ONLY from the registry / wrapped screeners, never fabricated. Screening reduces, not eliminates,
risk; it is a documented, audited safeguard, not a guarantee.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScreenKind = Literal["sequence_homology", "function_flag", "taxon_flag", "chimera_context", "oncogenic_flag"]
Severity = Literal["low", "medium", "high"]


class ScreenHit(BaseModel):
    """Frozen: a hazard hit's severity cannot be downgraded after screening (a mutable `severity` could be
    lowered to change the policy decision). Screens construct fresh hits, so immutability has no cost."""
    model_config = ConfigDict(frozen=True)

    kind: ScreenKind
    detail: str
    severity: Severity
    provenance: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)


def _assemble_cargo(design: dict) -> str | None:
    """Best-effort cargo sequence for the (optional) external homology screen. The baseline does not
    require it, function/taxon/chimera screens read declared annotations, not raw sequence."""
    return design.get("cargo_sequence") or design.get("cargo_seq")


def screen_design(design: dict, registry=None) -> list[ScreenHit]:
    """Run all hazard screens over a design. `design` is the structured proposal (declared function tags /
    Pfam domains / source taxon / delivery / sub-designs), NOT any free-text justification (the artifact
    decides, not the framing). Returns the list of typed hits (empty == no hazard signal)."""
    from pen_stack.safety.registry import HazardRegistry # lazy: registry imports ScreenHit from here
    # the default registry (no explicit override) wires the local Pfam/HMMER sequence screen as its
    # external_hook, so a raw cargo sequence is checked against the curated toxin families too, not just a
    # declared cargo_function. A caller wanting the bare, hookless registry still gets it via HazardRegistry.load().
    reg = registry or HazardRegistry.default()
    if not isinstance(design, dict):
        design = dict(design)
    hits: list[ScreenHit] = []
    hits += reg.function_flags(design) # toxin / pathogen-essential function domains
    hits += reg.oncogenic_flags(design) # oncogenic-manipulation pattern (mechanism/synonym-robust)
    hits += reg.taxon_flags(design) # regulated pathogen taxa
    hits += reg.chimera_context(design) # hazardous assembly of benign parts
    seq = _assemble_cargo(design)
    if seq:
        hits += reg.sequence_homology(seq) # local Pfam/HMMER screen (default) or a wrapped external screener
    return hits
