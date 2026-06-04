# Positioning - the writing side of genome engineering

## The gap

Genome **editing** (Cas9, base, and prime editors) is mature and well-benchmarked: CRISPOR, GUIDE-seq,
DeepCRISPR, off-target predictors, and many guide-design tools all answer *how to change a base in place*.
Genome **writing** - installing new information: inserting genes, flipping or excising kilobases, placing
programmable landing pads with serine integrases and RNA-guided bridge recombinases - is the harder, more
clinically transformative modality, and it has **no canonical reference layer and no benchmark**. Each lab
re-derives an ad-hoc safe-harbour shortlist, picks a writer from scattered papers, and has no genome-wide
off-target screen for the most programmable writers.

PEN-STACK fills the reference layer (the Writable Genome, the Writer Atlas, the Write Planner, the bridge
off-target engine). v3.1 adds the missing **evaluation layer**.

## M2: the Genome-Writing Bench complements editing-side benchmarks

The Genome-Writing Bench (`benchmarks/genome_writing_bench/`, v0.1) is, to our knowledge, the first
benchmark for the writing side. It is deliberately complementary, not competitive, with editing-side tools:

| Axis | Editing-side benchmarks | Genome-Writing Bench (writing-side) |
|---|---|---|
| Question | how to change a base in place | where to write, what writer, how to design, what risk |
| Unit | a guide / edit at a target | a site x writer x cargo x delivery plan |
| Tasks | on-target efficiency, off-target cleavage | site selection, writer selection, within-locus, off-target, intent, no-fabrication |
| Off-target | Cas9 cleavage (CRISPOR-class) | bridge-recombinase insertion (the unoccupied gap) |
| Agents | rarely scored | a grounded LLM-agent leaderboard with a no-fabrication hard gate |

## Design commitments (why it is trustworthy)

- **Deterministic scorers + documented ground truth.** No human or LLM judging; every task names a validated
  scorer and a DOI / measured dataset.
- **No circular labels.** The benchmark inherits the de-circularization gate: the retired targeted-intent
  recovery@k (definitional, not predictive) is excluded; site selection uses blind safe-harbour discovery.
- **No fabrication is a hard gate.** An LLM agent may reach the planner's numbers only by grounding every
  value in a tool call; inventing a number disqualifies it.
- **Honest scope.** Tasks are bounded by the available documented writes (small, survivorship-biased). The
  bench measures grounded planning quality and site/writer/off-target discrimination - not clinical outcome.
- **One-command, SHA-locked, reproducible** on a clean Docker image.

## Milestones

- **M1 - Writable Genome, hardened (v3.1 B,C,D,F).** Strong baselines (endogenous-expression, multi-mark,
  GSH rule-set), an AlphaGenome predicted-sequence + 3D structural-risk axis, Cargo Polish, and gated local
  adaptation. Framed for *Genome Biology / NAR / Bioinformatics*.
- **M2 - the Genome-Writing Bench + PEN-Agent (v3.1 E).** The benchmark and a grounded agent. Framed
  explicitly as the writing-side benchmark complementing editing-side tooling, for a datasets/benchmarks
  track or an agentic-bio venue.
- **M3 - Multiplex + guide QC (v3.1 G).** A translocation-risk screen and a bridge-RNA guide ranker.

## Citing / contributing

Preprint drafts are in `manuscripts/`. To put a solver on the leaderboard, see
[`benchmarks/genome_writing_bench/SUBMISSIONS.md`](../benchmarks/genome_writing_bench/SUBMISSIONS.md). The
no-fabrication gate (T6) is mandatory for any agent solver.
