"""Build the PEN-RAG corpus + its committed embeddings (v7.1).

Run where the pinned embedder (Ollama `nomic-embed-text`) is reachable. Writes:
  * data/rag_corpus.parquet   - the provenance-tagged chunks (SHA-locked)
  * data/rag_corpus_emb.npy   - the corpus embedding matrix (committed for replay)
Prints the chunk count, per-type breakdown, embedding shape, and the corpus SHA256.

Usage (on the VM, via the engine image with host networking for Ollama):
  docker run --rm --network host -e PYTHONPATH=/build -v ~/penstack:/build -w /build \\
      penstack:web python scripts/build_rag_corpus.py
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np

from pen_stack.rag.corpus import build_corpus, corpus_path, emb_path
from pen_stack.rag.embed import embed_corpus


def main(embed: bool = True) -> None:
    df = build_corpus()
    cp = corpus_path()
    cp.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cp, index=False)
    out = {"n_chunks": int(len(df)), "by_type": df["type"].value_counts().to_dict(),
           "corpus_sha256": hashlib.sha256(cp.read_bytes()).hexdigest()}
    if embed:
        emb = embed_corpus(df["text"].tolist())
        np.save(emb_path(), emb)
        out["emb_shape"] = list(emb.shape)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(embed="--no-embed" not in sys.argv)
