"""PEN-RAG retriever (v7.1).

Loads the committed corpus + its committed embedding matrix and returns the top-k chunks for a query by EXACT
cosine over the embeddings (semantic, via the live query embedder), with a deterministic token-Jaccard fallback
when no embedder is reachable. Exact cosine over a committed matrix is the reproducible equivalent of a vector
index at this corpus scale (hundreds of chunks) - FAISS is unnecessary.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from pen_stack.rag.corpus import emb_path, load_corpus
from pen_stack.rag.embed import embed_query, lexical_scores


@lru_cache(maxsize=1)
def _load():
    df = load_corpus()
    p = emb_path()
    emb = None
    if p.exists():
        m = np.load(p).astype("float32")
        if len(m) == len(df):  # guard against a stale embedding matrix
            emb = m
    return df, emb


def retrieve(query: str, k: int = 4) -> dict:
    df, emb = _load()
    texts = df["text"].tolist()
    qv = embed_query(query) if emb is not None else None  # v7.1.2: LRU-cached query embedding
    if qv is not None and emb is not None:
        scores = emb @ qv  # both L2-normalised -> dot product is cosine
        method = "semantic (nomic-embed-text)"
    else:
        scores = lexical_scores(query, texts)
        method = "lexical (jaccard fallback)"
    order = [int(i) for i in np.argsort(-scores)[:k]]
    hits = []
    for i in order:
        r = df.iloc[i]
        hits.append({"chunk_id": str(r.chunk_id), "text": str(r.text), "source_id": str(r.source_id),
                     "doi": str(r.doi) if r.doi else "", "type": str(r.type),
                     "scope_status": str(r.scope_status), "score": float(scores[i])})
    return {"query": query, "method": method, "hits": hits,
            "top_score": float(scores[order[0]]) if order else 0.0, "n_corpus": len(df)}
