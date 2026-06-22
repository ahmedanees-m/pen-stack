# WriteSpec-Bench (Stage A)

WriteSpec-Bench is the first prose-to-write-spec benchmark for genome writing: paired
`(plain-language request -> gold WriteSpec)`, grounded in real, well-documented genome-writing experiments
(cited per row). It is `benchmarks/writespec/` (corpus, splits, harness, metrics).

## Construction

- Each gold WriteSpec is the structured value a careful curator extracts: write-type, target kind, the gene
  (HGNC) or phenotype (MONDO) id, the cell (Cellosaurus / Cell Ontology) id, the cargo Sequence-Ontology role
  set, and the key constraints. Every ontology id was verified against the live services before commit.
- The **standard** subset is fully specified. The **ambiguity** subset is deliberately underspecified or
  ambiguous, to test that the extractor surfaces assumptions and asks clarifying questions rather than guessing.
- **Leakage control**: the test split is sealed and disjoint from train (`splits.json`); paraphrases do not
  co-occur across splits.

## Scoring (SO-Bench-style)

- **schema adherence**: the output validates as a typed `WriteRequest`.
- **structural fidelity**: write_type and target_kind match the gold.
- **value accuracy**: canonical-id match for gene / phenotype / cell, the cargo role set, and the listed
  constraints.
- **grounding**: on the ambiguity subset, clarifying questions fire and the inferred write_type is labelled;
  inferred-field labelling recall must be 100% (no field is set without provenance).

The baseline is the legacy keyword dictionary (`web.tools.parse_goal`), which emits raw tokens, not canonical
ids.

## Results (reported verbatim, deterministic extractor, not tuned to the sealed test)

- Sealed test: schema adherence 1.0, structural fidelity 1.0, value accuracy 0.964; baseline value accuracy
  0.464.
- Train: structural fidelity 1.0, value accuracy 0.988; baseline 0.407.
- Ambiguity subset: clarifying questions fire, inferred write_type labelled.
- Inferred-field labelling recall: 1.0.

The extractor beats the keyword-dict baseline because it resolves terms to verified ontology ids; the baseline
keeps raw tokens. The corpus is small and curated, grounded in real experiments; its value is bounded by curation
quality, reported verbatim. Two structural mismatches found during development were genuine extractor bugs (a
cell-line token mis-read as a gene; a disease prioritized over a named gene target), fixed in the extractor, not
papered over in the gold.

The full per-run metrics are in `benchmarks/writespec/writespec_bench_metrics.json`; re-run with
`python -m benchmarks.writespec.harness`.
