# Chat Head-to-Head (PEN-CHAT P-WS6, the punchline figure)

The figure that **measures** the no-fabrication claim rather than asserting it: on a shared query set (in-corpus +
out-of-corpus) three REAL systems answer, and we measure who fabricates.

- **PEN-CHAT** - the full grounded system (retrieve -> cite-or-silence -> guard, abstain below threshold);
- **vanilla RAG** - retrieve + prepend + ask the SAME LLM, with NO citation-or-silence and NO abstention;
- **ungrounded LLM** - the SAME LLM answering the bare question, no retrieval, no guard.

All three use the same local model (Ollama `qwen2.5:3b-instruct`); only the grounding harness differs.

## Result (`result.json`, 8 queries, 5 out-of-corpus)
| system | abstention on no-evidence | answered without grounding | 
|---|---|---|
| **PEN-CHAT** | **1.00** | **0.00** |
| vanilla RAG | 0.60 | 0.40 |
| ungrounded LLM | **0.00** | **1.00** |

The punchline: **PEN-CHAT abstains on every no-evidence (out-of-corpus) question and never answers one without a
grounded source; the ungrounded LLM answers all of them; vanilla RAG is in between.** `answered_without_grounding`
is the hallucination/false-grounding exposure - ~0 for PEN-CHAT, 1.0 for the ungrounded baseline.

This is a LIVE measurement (the baselines call a real LLM), so it is run once and its result committed; it is not a
CI unit test. Reproduce on a host with Ollama:
`PEN_RAG_NO_EMBED=0 python -m benchmarks.chat_headtohead.harness`.
