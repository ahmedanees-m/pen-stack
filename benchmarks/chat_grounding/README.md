# Chat Groundedness Benchmark (PEN-CHAT P-WS5, re-scoped v7.1.1)

Measures the corrected groundedness properties of the chat. The lane ANSWERS general and social questions
(labelled), grounds genome-writing questions in the cited corpus, and abstains ONLY on a specific unsourceable
empirical claim. The honesty metric is **false-grounding**, not answer-suppression. Deterministic (lexical
retriever, no LLM) -> reproducible in CI.

## Sealed set
`cases.jsonl` (SHA-locked) - `cited` (in-corpus genome-writing) + `general` (general knowledge) + `social` +
`abstain` (specific unsourceable empirical) cases.

## Result (`result.json`)
| metric | value |
|---|---|
| citation_coverage (on cited answers) | **1.0** |
| unsupported_claims_through_guard | **0** |
| **false_grounding_rate** (a general fact mislabelled as a PEN-STACK result) | **0.0** |
| **helpful_answer_rate** (general + social ANSWERED, not abstained) | **1.0** |
| abstention_on_specific_unsourceable | **1.0** |
| per-gold pass | cited 6/6 · general 4/4 · social 2/2 · abstain 2/2 |

The regression guard `helpful_answer_rate = 1.0` exists because v7.1.0 over-abstained (it declined "hi" and "what
is DNA"); v7.1.1 made retrieval additive, so general + social questions are answered (labelled) while the cited
answers keep citation coverage 1.0 and false-grounding stays 0.

Reproduce: `python -c "from benchmarks.chat_grounding.harness import run; print(run())"`.
