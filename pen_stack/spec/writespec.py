"""The WriteRequest schema (v6.14, Stage A, A-WS1): a typed, ontology-backed genome-writing request.

``WriteRequest`` is an SBOL3 profile expressed as a pydantic model. It carries the write semantics (write-type,
cargo with Sequence-Ontology roles, target locus/gene/att-site/phenotype, cell type, constraints) PLUS a
grounding discipline: a per-field provenance map (explicit | inferred | user | unresolved), the assumptions behind
every inferred field, clarifying questions for underspecified required fields, and the list of terms that could
not be resolved (kept null, never invented). A WriteRequest is a REQUEST, not a claim.

Round-trips: JSON always; SBOL3 via the real ``sbol3`` library when the ``[spec]`` extra is installed (native
Components + SO roles for interoperability, with the full typed spec carried losslessly in a PROV-O-namespaced
annotation); GenBank for a cargo component that carries a DNA sequence. ``to_legacy_design`` is the adapter that
emits the dict the existing downstream stages (verify / plan / safety) already consume, so the whole stack reads
one contract without a rewrite (gate A-G1).
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

WRITE_TYPES = ["insertion", "excision", "inversion", "replacement", "regulatory_rewrite",
               "landing_pad_install", "multiplex"]

ProvenanceKind = Literal["explicit", "inferred", "user", "unresolved"]

# id-format validators per ontology (a resolved id must match, else it is flagged not-valid).
_ID_FORMATS = {
    "SO": re.compile(r"^SO:\d{7}$"),
    "Cellosaurus": re.compile(r"^CVCL_[A-Z0-9]{4}$"),
    "CL": re.compile(r"^CL:\d{7}$"),
    "MONDO": re.compile(r"^MONDO:\d{7}$"),
    "HPO": re.compile(r"^HP:\d{7}$"),
    "ChEBI": re.compile(r"^CHEBI:\d+$"),
    "HGNC": re.compile(r"^[A-Z0-9-]+$"),
    "GRCh38": re.compile(r"^chr[0-9XYM]+(:\d+-\d+)?$"),
}


class Resolved(BaseModel):
    """A free-text term resolved to a canonical ontology id, with confidence and the candidate set when ambiguous."""
    text: str | None = None              # the surface term from the prose
    id: str | None = None                # canonical id (CVCL_0063, SO:0000167, MONDO:..., a gene symbol, ...)
    label: str | None = None             # canonical label
    ontology: str | None = None          # Cellosaurus | CL | SO | HGNC | MONDO | HPO | ChEBI | GRCh38
    confidence: float | None = None
    candidates: list[dict] = Field(default_factory=list)  # ranked alternatives when ambiguous
    note: str | None = None

    @property
    def resolved(self) -> bool:
        return self.id is not None


class CargoComponent(BaseModel):
    """A component to be written (CDS, promoter, insulator, attB, polyA, ...), with its SO/SBO role."""
    name: str
    role: Resolved | None = None         # Sequence-Ontology role
    sequence: str | None = None          # DNA sequence if given (else intent-only)
    length_bp: int | None = None


class Target(BaseModel):
    """Where the write goes: a locus, a gene, an att/landing site, or a phenotype goal."""
    kind: Literal["locus", "gene", "att_site", "phenotype", "unspecified"] = "unspecified"
    gene: Resolved | None = None
    locus: Resolved | None = None        # GRCh38 coordinate / safe-harbour
    att_site: str | None = None          # attB/attP/landing-pad id
    phenotype: Resolved | None = None    # MONDO/HPO disease goal


class Constraints(BaseModel):
    """The request's constraints (efficiency floor, scarless, safety switch, copy number, guardrails, delivery)."""
    efficiency_floor: float | None = None
    scarless: bool | None = None
    safety_switch_required: bool | None = None
    copy_number: int | None = None
    germline: bool | None = None         # germline guardrail (True = a germline edit was requested -> flagged)
    max_cargo_bp: int | None = None
    delivery_limit: str | None = None    # e.g. "non_integrating", "AAV_only"
    inducer: Resolved | None = None      # ChEBI small-molecule inducer / selection agent


class WriteRequest(BaseModel):
    """A typed, ontology-backed, machine-checkable genome-writing request (an SBOL3 profile). A REQUEST, not a claim.

    Every field that was not explicit in the source prose is recorded in ``provenance`` as ``inferred`` (with the
    rationale in ``assumptions``); a required field that is unspecified or ambiguous yields a ``clarifications``
    question rather than a guess; a term that could not be resolved is listed in ``unresolved`` and kept null.
    """
    write_type: str                      # one of WRITE_TYPES
    cargo: list[CargoComponent] = Field(default_factory=list)
    target: Target = Field(default_factory=Target)
    cell_type: Resolved | None = None
    constraints: Constraints = Field(default_factory=Constraints)
    # --- grounding discipline ---
    provenance: dict[str, ProvenanceKind] = Field(default_factory=dict)  # field -> origin
    assumptions: list[str] = Field(default_factory=list)                 # inferred fields + rationale
    clarifications: list[str] = Field(default_factory=list)              # questions for underspecified fields
    unresolved: list[str] = Field(default_factory=list)                  # terms that could not be resolved
    free_text_note: str | None = None    # the original prose (the cargo-function the Guardian must screen)
    extensions: dict[str, Any] = Field(default_factory=dict)            # edge intents the schema does not cover

    # ---- validation -------------------------------------------------------------------------------------------
    def ontology_validation(self) -> dict[str, Any]:
        """Check every resolved field's id against its ontology id-format. Returns the per-field verdict."""
        bad: list[dict] = []
        checked = 0
        for field, r in self._resolved_fields().items():
            if r.id is None or r.ontology is None:
                continue
            checked += 1
            fmt = _ID_FORMATS.get(r.ontology)
            if fmt is not None and not fmt.match(r.id):
                bad.append({"field": field, "id": r.id, "ontology": r.ontology})
        return {"checked": checked, "invalid": bad, "all_valid": not bad}

    def _resolved_fields(self) -> dict[str, Resolved]:
        out: dict[str, Resolved] = {}
        if self.cell_type:
            out["cell_type"] = self.cell_type
        if self.target.gene:
            out["target.gene"] = self.target.gene
        if self.target.locus:
            out["target.locus"] = self.target.locus
        if self.target.phenotype:
            out["target.phenotype"] = self.target.phenotype
        if self.constraints.inducer:
            out["constraints.inducer"] = self.constraints.inducer
        for i, c in enumerate(self.cargo):
            if c.role:
                out[f"cargo[{i}].role"] = c.role
        return out

    @property
    def is_grounded(self) -> bool:
        """No fabrication: every field is either explicit, user, inferred-and-labelled, or unresolved-and-null."""
        return self.ontology_validation()["all_valid"]

    # ---- the downstream adapter (gate A-G1) -------------------------------------------------------------------
    def to_legacy_design(self) -> dict:
        """Emit the dict the existing downstream stages (verify / plan / safety / delivery) already consume.

        This is the wrap-not-rewrite adapter: the whole stack reads ``WriteRequest`` through this one mapping
        instead of a per-stage rewrite. Unspecified fields fall back to the stack's documented defaults.
        """
        cargo_bp = self.constraints.max_cargo_bp
        if cargo_bp is None:
            cargo_bp = sum((c.length_bp or 0) for c in self.cargo) or None
        gene = self.target.gene.id if (self.target.gene and self.target.gene.id) else None
        locus = self.target.locus.id if (self.target.locus and self.target.locus.id) else None
        chrom = None
        if locus and locus.startswith("chr"):
            chrom = locus.split(":")[0]
        design = {
            "write_type": self.write_type,
            "gene": gene,
            "chrom": chrom,
            "cargo_bp": cargo_bp,
            "cell_type": self.cell_type.id if (self.cell_type and self.cell_type.id) else None,
            # delivery_limit holds either a named vehicle or the "non_integrating" flag
            "delivery_vehicle": (self.constraints.delivery_limit
                                 if self.constraints.delivery_limit not in (None, "non_integrating") else None),
            "non_integrating": (self.constraints.delivery_limit == "non_integrating") or None,
            "installed_att": bool(self.target.att_site),
            "cargo_function": self.free_text_note,
        }
        return {k: v for k, v in design.items() if v is not None}

    # ---- serialization ----------------------------------------------------------------------------------------
    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, s: str) -> "WriteRequest":
        return cls.model_validate_json(s)

    def to_sbol3(self, namespace: str = "https://penstack.org/writespec") -> str:
        """Serialize to SBOL3 (sorted N-triples) via the ``sbol3`` library: native Components + Sequence-Ontology
        roles for interoperability, with the full typed spec carried losslessly in a PROV-O-namespaced annotation.

        Requires the ``[spec]`` extra (``pip install sbol3``); raises ImportError otherwise (never fabricates).
        """
        import sbol3
        sbol3.set_namespace(namespace)
        doc = sbol3.Document()
        top = sbol3.Component(f"write_{self.write_type}", sbol3.SBO_DNA)
        top.name = f"WriteRequest: {self.write_type}"
        # native SO roles for the cargo (interoperable with the SBOL3 / GenBank ecosystem)
        for i, c in enumerate(self.cargo):
            sub = sbol3.Component(f"cargo_{i}_{re.sub(r'[^A-Za-z0-9]', '_', c.name)[:24]}", sbol3.SBO_DNA)
            if c.role and c.role.id and c.role.ontology == "SO":
                sub.roles = [f"https://identifiers.org/SO:{c.role.id.split(':')[1]}"]
            if c.sequence:
                seq = sbol3.Sequence(f"seq_{i}", elements=c.sequence.upper(), encoding=sbol3.IUPAC_DNA_ENCODING)
                doc.add(seq)
                sub.sequences = [seq.identity]
            doc.add(sub)
            top.features.append(sbol3.SubComponent(sub))
        # the full typed spec rides losslessly as a custom (PROV-O-style) annotation
        top.write_spec_json = sbol3.TextProperty(top, f"{namespace}#writeSpecJson", 0, 1)
        top.write_spec_json = self.to_json()
        doc.add(top)
        return doc.write_string(sbol3.SORTED_NTRIPLES)

    @classmethod
    def from_sbol3(cls, ttl: str, namespace: str = "https://penstack.org/writespec") -> "WriteRequest":
        """Reconstruct a WriteRequest from its SBOL3 serialization (the lossless PROV-O annotation)."""
        import sbol3
        sbol3.set_namespace(namespace)
        doc = sbol3.Document()
        doc.read_string(ttl, sbol3.SORTED_NTRIPLES)
        for obj in doc.objects:
            prop = f"{namespace}#writeSpecJson"
            val = obj._properties.get(prop)
            if val:
                raw = str(val[0])
                return cls.from_json(raw)
        raise ValueError("no WriteRequest annotation found in the SBOL3 document")

    def to_genbank(self) -> str | None:
        """Export the cargo as a GenBank record when it carries a DNA sequence; None for an intent-only spec."""
        seqs = [c for c in self.cargo if c.sequence]
        if not seqs:
            return None
        from io import StringIO

        from Bio.Seq import Seq
        from Bio.SeqFeature import FeatureLocation, SeqFeature
        from Bio.SeqRecord import SeqRecord
        full = "".join(c.sequence.upper() for c in seqs)
        rec = SeqRecord(Seq(full), id="WRITESPEC", name="WriteSpec", description=f"{self.write_type} cargo")
        rec.annotations["molecule_type"] = "DNA"
        pos = 0
        for c in seqs:
            ln = len(c.sequence)
            role = (c.role.label if (c.role and c.role.label) else c.name)
            rec.features.append(SeqFeature(FeatureLocation(pos, pos + ln), type="misc_feature",
                                           qualifiers={"label": [role]}))
            pos += ln
        buf = StringIO()
        from Bio import SeqIO
        SeqIO.write(rec, buf, "genbank")
        return buf.getvalue()
