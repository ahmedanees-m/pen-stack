"""PEN-RAG embedding client (v7.1).

A pinned local embedder (`nomic-embed-text` via the already-running Ollama) for semantic retrieval, with a
deterministic, model-free **lexical fallback** so the General lane still retrieves (degraded, but honest) when no
embedder is reachable - e.g. in CI or if Ollama is down. The CORPUS embeddings are computed once at build time and
committed (`data/rag_corpus_emb.npy`); only the live QUERY is embedded at runtime, so retrieval stays reproducible.
"""
from __future__ import annotations

import json
import os
import urllib.request

import numpy as np

EMBED_MODEL = os.getenv("PEN_RAG_EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
_TIMEOUT = int(os.getenv("PEN_RAG_EMBED_TIMEOUT", "30"))
# nomic-embed-text is trained with task prefixes; using them is REQUIRED for retrieval to separate relevant from
# irrelevant (without them every pair sits in a narrow high-cosine band and abstention cannot discriminate).
_PREFIX = {"query": "search_query: ", "document": "search_document: "}


def embed_text(text: str, task: str = "query") -> np.ndarray | None:
    """L2-normalised embedding of one string via Ollama (with the nomic task prefix), or None if unreachable."""
    if os.getenv("PEN_RAG_NO_EMBED") == "1":
        return None
    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "prompt": _PREFIX.get(task, "") + (text or "")}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            vec = json.loads(r.read().decode())["embedding"]
        v = np.asarray(vec, dtype="float32")
        n = float(np.linalg.norm(v))
        return v / n if n else v
    except Exception:  # noqa: BLE001 - any failure -> caller uses the lexical fallback
        return None


def embed_corpus(texts: list[str]) -> np.ndarray:
    """Embed the corpus DOCUMENTS at BUILD time. Raises if the embedder is unreachable (the build must be
    deterministic and must never silently fall back to a different representation)."""
    out = []
    for t in texts:
        v = embed_text(t, task="document")
        if v is None:
            raise RuntimeError(f"embedder '{EMBED_MODEL}' unreachable at {OLLAMA_HOST}; cannot build corpus embeddings")
        out.append(v)
    return np.vstack(out).astype("float32")


# --- deterministic, model-free lexical fallback (content-token Jaccard) --------------------------------------
# Stopwords are dropped so the fallback discriminates on CONTENT words: an out-of-corpus query (e.g. "what is the
# capital of France") must not match a genome-writing chunk via shared function words and slip past the abstention.
_STOP = frozenset((
    "the and for are was were that this with from have has had not but you your his her its our their they them "
    "what which who whom whose when where why how does did doing done can could should would will shall may might "
    "into onto over under above below than then them they about after before between because while during each "
    "any all some more most much many few any both either neither nor yet via per such only also same other "
    "one two three get got make made use used using like just very too here there out off own").split())


def tokenize(s: str) -> set[str]:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in (s or "")).split()
            if len(w) > 2 and w not in _STOP}


def lexical_scores(query: str, texts: list[str]) -> np.ndarray:
    """Jaccard overlap of the query tokens with each document's tokens. Deterministic; no model."""
    q = tokenize(query)
    if not q:
        return np.zeros(len(texts), dtype="float32")
    out = np.zeros(len(texts), dtype="float32")
    for i, t in enumerate(texts):
        d = tokenize(t)
        out[i] = len(q & d) / len(q | d) if d else 0.0
    return out
