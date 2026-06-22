# The WriteSpec profile (Stage A)

WriteSpec is a typed, ontology-backed, machine-checkable representation of a genome-writing request. It replaces
the keyword parser with one contract every downstream stage consumes, and it is an SBOL3 profile, so it is
interoperable with the genetic-design-automation ecosystem and GenBank from day one. A WriteSpec is a request,
not a claim.

## The type

`WriteRequest` (`pen_stack/spec/writespec.py`) carries:

- **write_type**: one of insertion, excision, inversion, replacement, regulatory_rewrite, landing_pad_install,
  multiplex.
- **cargo**: a list of components, each with a Sequence-Ontology role (promoter `SO:0000167`, CDS `SO:0000316`,
  polyA signal `SO:0000551`, insulator `SO:0000627`, ...) and an optional sequence and length.
- **target**: the edit site, as a gene (HGNC), a locus (GRCh38 coordinate), an att/landing site, or, when only a
  disease goal is given, a phenotype (MONDO). A named gene or att site is the target; a disease is attached as the
  goal.
- **cell_type**: a Cellosaurus cell line (HEK293T `CVCL_0063`) or a Cell-Ontology cell type (T cell `CL:0000084`),
  carrying the irreducible subline / karyotype-drift caveat.
- **constraints**: efficiency floor, scarless, safety-switch-required, copy number, germline guardrail, max cargo
  bp, delivery limit / vehicle, and a ChEBI small-molecule inducer.

## The grounding discipline

Every field records its provenance in the `provenance` map: `explicit` (stated in the prose), `inferred`
(defaulted, with the rationale in `assumptions`), `user` (supplied through a structured override), or
`unresolved`. A required field that is unspecified or ambiguous yields a `clarifications` question rather than a
guess. A term that cannot be resolved is listed in `unresolved` and its field stays null. Nothing is invented.

All curated ontology ids were verified against the live services (Cellosaurus, EBI OLS for SO / MONDO / CL /
ChEBI) before they were committed; a resolver degrades to `unresolved`, never a fabricated id.

## Round-trips and the downstream adapter

- **JSON**: always available (`to_json` / `from_json`), lossless.
- **SBOL3**: `to_sbol3` / `from_sbol3` via the real `sbol3` library (the `[spec]` extra). The export emits native
  Components with Sequence-Ontology roles for interoperability and carries the full typed spec losslessly in a
  PROV-O-namespaced annotation.
- **GenBank**: `to_genbank` exports the cargo as a GenBank record when it carries a DNA sequence (intent-only
  specs return None).
- **`to_legacy_design`**: the adapter that emits the dict the existing stages (verify / plan / safety / delivery)
  already consume, so the whole stack reads one contract without a per-stage rewrite.

## Feasibility

`pen_stack/spec/satisfy.py` tests the necessary conditions a write must meet by wrapping the existing stages:
reachability (the writable-genome atlas), deliverability (the Stage D recommender), and legality (the Stage F
rule set, via the repair-oriented proof object). It returns feasible or infeasible plus the named blocking
constraint(s) and repair hints, so an agent can repair the spec and re-check. Feasibility is necessary, not
sufficient: it rules out unreachable / undeliverable / illegal, not whether the write will work (that is the
downstream stages' calibrated prediction).

## Surfaces

- REST `POST /api/writespec` (body `{prose, overrides?, check_feasibility?}`).
- MCP `writespec_parse`.
- The web "Describe a Write" builder page.
