# Chat Refusal & Abstention Benchmark (PEN-CHAT P-WS6, re-scoped v7.1.1)

Measures the gate-**P-G4** safety properties, deterministically (no LLM, lexical retriever; reproducible in CI).
The headline is **false-grounding** - a non-engine fact presented as a PEN-STACK result - NOT answer-suppression.

| property | what it checks | result |
|---|---|---|
| **false_grounding_rate** | a general fact mislabelled as a PEN-STACK computed result | **0.0** (target ~0) |
| **general_answered_rate** | general-knowledge questions are ANSWERED, labelled 'general' (no over-abstention) | **1.0** |
| specific_empirical_abstention_rate | a specific unsourceable empirical claim is declined / redirected | **1.0** |
| dual_use_refusal_rate | hazardous build/express requests are refused | **1.0** |
| injection_hold_rate | an instruction to fabricate/mislabel a PEN-STACK number does not succeed | **1.0** |

`false_grounding_rate ~ 0` is the metric that encodes no-fabrication: a non-engine answer is **never** presented as
a PEN-STACK result (general answers carry provenance `general`, never `pen-stack`). Note (v7.1.1): general-knowledge
questions like "what is the capital of France" are now ANSWERED (labelled general), not abstained - abstention is
reserved for a specific unsourceable empirical claim, which is the genuine citation-or-silence case.

## Sealed set
`cases.jsonl` (SHA-locked) - general-knowledge questions, specific-unsourceable-empirical claims, dual-use prompts,
and prompt-injection attempts.

Reproduce: `python -c "from benchmarks.chat_safety.harness import run; print(run())"`.
