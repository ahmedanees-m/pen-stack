# The oracle mesh

PEN-STACK wraps the biomolecular foundation models (AlphaGenome, Evo2, AlphaFold3, Boltz-2, Chai-1, Protenix,
ESM3, RFdiffusion, ProteinMPNN, ViennaRNA, and the bridge energetics model) behind one result contract. Every
oracle, however different internally, answers through the same `OracleResult`: a value, its provenance
(model + version), the model's own native uncertainty, and a scope card. Three invariants are encoded in the
type itself:

1. A generative output is a candidate, never a claim. A generated sequence, structure or backbone is a proposal
   that must pass writer-verification before it can enter a claim path (`as_claim()` raises on a candidate).
2. One contract for every oracle. Provenance and the oracle's native uncertainty are always carried; every call
   is cache-keyed on inputs, model and version.
3. Scope is explicit. Each result names its scope card and carries an `extrapolating` flag, so the evidence that
   these models do not generalize outside their training envelope is labelled, not hidden.

## Binding affinity (Boltz-2)

The affinity oracle (`pen_stack.oracles.affinity`) wraps the Boltz-2 protein-ligand affinity head (Boltz-2, MIT,
DOI 10.1101/2025.06.14.659707). For a protein and a small-molecule ligand it returns a binder probability and a
predicted affinity value (a log(IC50), micromolar-scale number, lower = stronger), with native uncertainty taken
from the model's own outputs. The head is protein-small-molecule only: protein-protein and protein-DNA pairs are
returned as out-of-scope (extrapolating). Pair types in scope include the small-molecule inducer that switches a
genome writer (for example 4-hydroxytamoxifen and the ERT2 ligand-binding domain), a capsid-binding ligand, and
an effector drug.

The affinity backend is a long GPU batch (around ten to thirty minutes including the MSA), so it runs off the
request path and the result is cached. The request path is cache-or-abstain: a request with no cached run defers
(`available=False`) rather than blocking the chat or fabricating a value.

## Per-oracle reliability

`configs/oracles/reliability.yaml` records each oracle's published reliability on public benchmarks, reported
verbatim with citation (`pen_stack.oracles.reliability`). These numbers are the wrapped model's accuracy as
reported by its authors or the community, not a claim about this stack's own accuracy and not re-computed here.
The verified anchor is the Boltz-2 affinity head's FEP+ (OpenFE) Pearson r of about 0.62 (paper-reported); its
CASP16 affinity-challenge ranking is recorded as a self-report, not independently verified. For the structure and
sequence oracles the registry names the benchmark each is evaluated on (CASP and CAMEO for structure, ProteinGym
and FLIP for variant effect) with citations, and leaves the numeric value null where a verbatim score was not
independently verified rather than inventing one.

Reliability is surfaced in `GET /api/oracles`, in the MCP `oracle_query` tool, and in the web Oracle Mesh page,
so a confident-looking value is read alongside how reliable the model that produced it actually is.

## Disagreement to uncertainty

Where redundant numeric oracles are available (for example the structure predictors), agreement is a confidence
signal and disagreement widens the reported interval. The consensus combines the available oracles and sets the
reported native uncertainty to the largest member uncertainty plus half the cross-oracle spread. This widening is
monotonic in the spread, checked by `disagreement_widens_monotonically` and reported by Oracle-Bench.

## Held oracles

The structure oracles (AlphaFold3 / Boltz-2 / Chai-1 / Protenix) over full writer-substrate and att-site
complexes are held: a full complex prediction is a long GPU or cloud batch run off-request and cached
(`pen_stack.oracles.structure_run`). The request path replays the cache or abstains; it never runs the long job
inline.

## Surfaces

- `GET /api/oracles` (optional `?probe=true`): per-oracle execution, latency class, live status and published
  reliability, plus the disagreement-to-interval check.
- `POST /api/oracle/affinity`: a protein-ligand binding-affinity query (cache-or-abstain).
- MCP `oracle_query`: the same, for an agent.
- Web: the Oracle Mesh page.
