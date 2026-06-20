"""WT-KB schema - the Writer-Targeting Knowledge Base row model (Phase 0, Step 0.2).

One row per writer family/representative system: its targeting requirements and a reachability tier.
This is the spine of the Writer Atlas and the reachability layer of the Writable Genome. Every
targeting field must carry at least one DOI in ``key_dois`` - nothing is asserted without a citation.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MechBucket(str, Enum):
    DSB_NUCLEASE = "DSB_NUCLEASE"
    DSB_FREE_RECOMBINASE = "DSB_FREE_TRANSEST_RECOMBINASE"
    TRANSPOSASE = "TRANSPOSASE"


class Tier(str, Enum):
    T1 = "Tier1_scannable" # bridge/seek cores, PE-installable att
    T2 = "Tier2_context_candidate" # CAST, native pseudo-att integrases (candidate - requires validation)
    T3 = "Tier3_not_predictable" # retroelement preferences


class Confidence(str, Enum):
    MEASURED = "measured"
    INFERRED = "inferred"
    PREDICTED = "predicted"


class WriterEntry(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    family: str
    representative_system: str
    uniprot: str | None = None
    mechanism_bucket: MechBucket
    pfam_signature: list[str]
    targeting_modality: str # RNA-guided | fixed-att | DDE-spacing | PE-installable
    target_site_spec: str # e.g. "bipartite ~14 nt, central CT dinucleotide core"
    guide_architecture: str # e.g. "bridge RNA: TBL(LTG/RTG)+DBL(LDG/RDG)"
    cargo_mechanism: str # intrinsic | fixed-donor | templated
    cargo_capacity_bp: int | None = None
    dsb_free: bool
    length_aa: int | None = None
    human_cell_activity: str | None = None # measured value + source, or "not measured"
    deliverability: str # AAV | split-AAV | mRNA-RNP
    reachability_tier: Tier
    reachability_constraints: str # rules a genome scan must apply
    confidence: Confidence = Confidence.MEASURED
    key_dois: list[str] = Field(min_length=1)

    @field_validator("key_dois")
    @classmethod
    def _nonempty_dois(cls, v: list[str]) -> list[str]:
        if not v or not all(d.strip() for d in v):
            raise ValueError("every WT-KB row must carry >=1 non-empty DOI (sourcing rule)")
        return v
