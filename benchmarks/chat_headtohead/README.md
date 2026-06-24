# Chat Head-to-Head (PEN-CHAT P-WS6, re-framed v7.1.1)

The corrected punchline measures the property that actually encodes no-fabrication - **provenance labelling and
false grounding** - NOT answer suppression. All three systems ANSWER general questions (a labelled general answer
is honest); the differentiator is whether they tell you *what kind* of answer it is, and whether they invent a
statistic for a made-up entity.

Three REAL systems on a shared set, all using the same local model (Ollama `qwen2.5:3b-instruct`); only the
grounding harness differs.

## Result (`result.json`, 6 queries: 3 general + 3 specific-unsourceable)
| system | provenance-labelled | fabricated a stat for a made-up entity |
|---|---|---|
| **PEN-CHAT** | **1.00** | **0.00** |
| vanilla RAG | 0.00 | 0.67 |
| ungrounded LLM | 0.00 | 0.67 |

- **provenance_labelled_rate** - every PEN-CHAT answer carries its lane + provenance (general / literature-cited /
  pen-stack / abstained), so a reader can never mistake a general-knowledge answer for a platform result. The
  ungrounded baselines carry NO provenance - every answer looks equally authoritative.
- **fabricated_stat_on_unsourceable_rate** - asked for a specific number about a made-up writer/locus, PEN-CHAT
  routes to the engine or cites the corpus (a grounded number) or abstains - it never presents an *ungrounded*
  number; the baselines invent a confident statistic 67% of the time.

This is the honest claim: PEN-CHAT answers general questions like any assistant, but it never presents an unsourced
fact as a platform result - measured - and the baselines do.

Live measurement (the baselines call a real LLM); result committed. Not a CI unit test (a CI test reads the result).
Reproduce on a host with Ollama: `PEN_RAG_NO_EMBED=0 python -m benchmarks.chat_headtohead.harness`.
