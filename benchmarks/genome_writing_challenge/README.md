# The Genome-Writing Challenge

An **open, recurring, held-out** benchmark for the *writing* side of genome engineering: the CASP /
Virtual-Cell-Challenge model, applied to *where / what / how to write*. Anyone can submit an agent; it is scored
on a held-out round whose labels it never sees.

## Why

Editing-side tooling has benchmarks; the **writing** side did not have an open, externally-submittable one.
PEN-STACK's internal Genome-Writing Bench (v0.3.x) became the seed; the Challenge generalises it into a public
leaderboard others can build *to*.

## How to submit

```python
from benchmarks.genome_writing_challenge.harness import Submission, evaluate

def my_predict(public_input: dict):
    # public_input = {"task_id", "family", "design", "instructions"}; the label is NOT included
    if public_input["family"] == "legality":   return True            # is this design legal?
    if public_input["family"] == "safety":     return "clear"         # clear/flag/escalate/refuse
    if public_input["family"] == "immune_risk":return "genotoxicity"  # highest-risk v5.6 axis
    return None                                                       # abstaining is allowed (scores 0)

result = evaluate(Submission(name="my-agent", predict_fn=my_predict), round_id="2026R1")
print(result["aggregate"], result["by_family"])
```

Run the reference: `python benchmarks/genome_writing_challenge/run.py`.

## Task families (this round)

| Family | Public input | Held-out label (released after the round) |
|---|---|---|
| `legality` | a design | legal/illegal (from the validated v3.3 rules) |
| `safety` | a design | clear/flag/escalate/refuse (from the v5.7 Guardian) |
| `immune_risk` | a design | the highest-risk immune axis (from the v5.6 profile) |

*(Future rounds add write-types, adversarial, outcome, experiment-design, and closed-loop families.)*

## Rules

- **Held-out.** Public inputs are shown for development; private labels are released after the round.
- **No circular labels.** Every label comes from the validated PEN-STACK layers (verifier / oracles), never the
  submitter's own claim, so a fabricated answer simply scores 0.
- **No fabrication.** A submission may answer or abstain; it must not crash. Grounding is enforced by the labels.
- **Reproducible.** Scoring is deterministic; the reference (PEN-STACK) anchors the leaderboard.

See `SUBMISSIONS.md` and [`docs/integrations.md`](../../docs/integrations.md).
