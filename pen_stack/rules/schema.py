"""Rule / Design / Verdict schema, the laws of genome writing as data.

A *rule is data, not code* (Principle 1): every constraint is a versioned record with an id, a kind
(`hard_reject` | `soft_penalty` | `scope_flag`), the mechanism it encodes, a controlling parameter, a
provenance/citation, a test reference, and the name of the registered *evaluator* that executes it. Code
executes rules; it does not contain them. The evaluators (``pen_stack/rules/evaluators.py``) wrap the
EXISTING validated functions (target_site, fold_qc, delivery, multiplex), so relocation changes nothing about
the decisions, only makes them enumerable, queryable, and citation-backed (proven by the parity test).

Legality and confidence are different axes (Principle 2): ``legal`` = every applicable hard rule passes;
confidence is the calibrated trust attached separately by the verifier. Never collapse.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuleKind = Literal["hard_reject", "soft_penalty", "scope_flag"]
RuleStatus = Literal["pass", "violate", "flag", "scope", "not_applicable"]
RuleCategory = Literal["reachability", "fold", "payload", "multiplex", "delivery", "compliance"]


class Rule(BaseModel):
    """A single law of genome writing, expressed as data. Frozen: the pinned, citation-backed rules are
    immutable once loaded, so a law cannot be silently edited at runtime."""
    model_config = ConfigDict(frozen=True)

    id: str
    kind: RuleKind
    category: RuleCategory
    mechanism: str # one-line statement of what physical fact it encodes
    evaluator: str # registered evaluator fn name (rules/evaluators.py)
    param: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict) # {doi: [...], note: ...}
    test_ref: str | None = None
    scope: str | None = None # limit (e.g. "screen, not activity guarantee")


class Ruleset(BaseModel):
    version: str
    rules: list[Rule]

    def by_category(self, category: str) -> list[Rule]:
        return [r for r in self.rules if r.category == category]

    def get(self, rule_id: str) -> Rule | None:
        return next((r for r in self.rules if r.id == rule_id), None)


class Design(BaseModel):
    """A proposed genomic write submitted for verification. Permissive: evaluators that lack their inputs
    return ``not_applicable`` rather than failing, so a partial design is still checkable.

    Biosecurity screening. The safety gate reads hazard content ONLY from these declared fields:
    ``cargo_function``, ``function_annotation``, ``goal_function``, ``source_taxon``, ``organism``,
    ``host_taxon``, ``cargo_seq``, ``cargo_sequence`` (text) and ``function_tags``, ``pfam_domains``,
    ``annotations`` (lists). Of these, only ``cargo_seq`` is a formal field here; the rest are passed as extra
    keys (``model_config`` allows extra) and are screened all the same. Content placed in ``edit_intent`` or
    any other free-text/framing field is deliberately NOT screened, framing is stripped before screening so a
    hazardous design cannot be re-labelled "defensive" to pass. Consequently a verdict with
    ``declared_signal=False`` means "no screenable content was declared, so nothing was screened", which is NOT
    the same as "screened and found safe". Put hazard-relevant content in the fields above."""
    write_type: str = "insertion"
    gene: str | None = None
    chrom: str | None = None
    site_seq: str | None = None # sequence window at the target site (reachability)
    writer_family: str | None = None
    writer_output_form: Literal["DNA", "mRNA", "RNP"] | None = None
    installed_att: bool = False # a pre-installed landing pad declared
    cargo_bp: int | None = None
    cargo_seq: str | None = None
    delivery_vehicle: str | None = None
    cell_type: str | None = None
    edit_intent: str | None = None
    no_integration: bool = False # goal forbids genomic integration
    target_guide: str | None = None # bridge-RNA target-binding loop (fold)
    donor_guide: str | None = None # bridge-RNA donor-binding loop (fold)
    edits: list[dict] = Field(default_factory=list) # multi-edit plan (multiplex)

    model_config = {"extra": "allow"} # forward-compatible with new dimensions


class RuleResult(BaseModel):
    """Frozen: a rule's outcome cannot be edited after evaluation, so `status`/`kind` (and therefore
    `is_blocking`) cannot be flipped to turn a violation into a pass downstream."""
    model_config = ConfigDict(frozen=True)

    rule_id: str
    kind: RuleKind
    category: RuleCategory
    status: RuleStatus
    reason: str
    citation: list[str] = Field(default_factory=list)
    value: Any = None # optional numeric (penalty/score), provenance-tagged

    @property
    def is_blocking(self) -> bool:
        return self.kind == "hard_reject" and self.status == "violate"
