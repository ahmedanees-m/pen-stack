# Chat Groundedness Benchmark (PEN-CHAT P-WS5)

Measures the two pre-registered groundedness properties of the chat's General (retrieval) lane (gate **P-G3**):

- **citation coverage = 1.0** - every factual line of a grounded answer maps to a cited source (`[source . DOI]`);
- **0 unsupported claims through the guard** - a grounded answer never lacks sources and no `[unverified]` number
  survives; an out-of-corpus question **abstains** rather than answer from priors.

## Sealed set
`cases.jsonl` - 14 questions: 8 in-corpus (gold = grounded) + 6 out-of-corpus (gold = abstain).

## Result (`result.json`)
| path | citation coverage | unsupported | abstention (OOC) | grounding (in-corpus) |
|---|---|---|---|---|
| **production (semantic, nomic-embed-text)** | **1.0** | **0** | **1.0** | **1.0** |
| CI fallback (lexical, model-free) | 1.0 | 0 | 0.833 | 0.875 |

Both core P-G3 gates (**citation coverage = 1.0**, **0 unsupported claims**) hold on **both** retrievers. The
model-free lexical fallback (used in CI so the test needs no Ollama) abstains/grounds slightly less than the
semantic path; this is reported, not hidden - the production lane is semantic, where abstention and grounding are
both 1.0 on this set.

Reproduce (lexical, CI): `python -c "from benchmarks.chat_grounding.harness import run; print(run())"`.
Semantic (needs Ollama `nomic-embed-text`): set `PEN_RAG_NO_EMBED=0` and run the same.
