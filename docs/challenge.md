# The Genome-Writing Challenge (v5.13)

PEN-STACK's accumulated bench tasks (v3.4→v5.12) become an **open, recurring, held-out** benchmark others build
*to* — the CASP / Virtual-Cell-Challenge model for the *writing* side of genome engineering.

```bash
python benchmarks/genome_writing_challenge/run.py          # score the PEN-STACK reference on the current round
```

## How it works (`benchmarks/genome_writing_challenge/harness.py`)

An external agent submits a `Submission(name, predict_fn)`. `evaluate(submission, round_id)` scores
`predict_fn(public_input) -> answer` on a **held-out** round:

- each `public_input` names its `family` + `task_id` + `design` + `instructions` — **never the label**;
- the private label is computed by the **validated PEN-STACK layers** (the v3.3 rules, the v5.7 Guardian, the
  v5.6 immune profile) — so **no task uses a circular label**; a fabricated answer cannot match an invented label
  and simply scores 0;
- a **no-fabrication** audit runs on every submission;
- task families generalise the internal bench: `legality`, `safety`, and an **immune-risk** task grounded in the
  v5.6 oracles (future rounds add write-types, adversarial, outcome, experiment-design, closed-loop).

The **reference** submission (PEN-STACK itself) anchors the leaderboard at 1.0 by construction.

## Why it is honest

- **Held-out + private labels** released after a round — you cannot reverse-fit.
- **No circular labels** — labels are mechanistic/verifier facts, not the agent's own claim.
- **Reproducible** — deterministic scoring, version-pinned.
- **Immune-risk first-class** — an immune-risk task draws directly on the v5.6 profile.

See [`benchmarks/genome_writing_challenge/README.md`](../benchmarks/genome_writing_challenge/README.md),
`SUBMISSIONS.md`, and [Integrations](integrations.md).
