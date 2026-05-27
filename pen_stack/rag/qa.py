"""PenStackQA: RAG Q&A using local Ollama + ChromaDB.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (CPU, ~80 MB).
LLM: Ollama Llama 3.1 8B Instruct (GPU, 4-bit quant).
Vector DB: ChromaDB persistent client at data/rag_db/.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
COLLECTION_NAME = "pen_compare_docs"
TOP_K = 5
CHUNK_SIZE = 400  # words per chunk
CHUNK_OVERLAP = 80  # word overlap between adjacent chunks
MAX_TOKENS = 384  # max tokens in LLM response

_SKIP_DIRS = {"rag_db", ".git", "__pycache__", ".github"}
_INDEX_EXTS = (".md", ".yaml", ".yml", ".json", ".txt")


class PenStackQA:
    def __init__(self, db_path: str | Path = "data/rag_db") -> None:
        self._db_path = Path(db_path)
        self._embedder = SentenceTransformer(EMBED_MODEL)
        self._chroma = chromadb.PersistentClient(
            path=str(self._db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._chroma.get_or_create_collection(COLLECTION_NAME)

    # ── Indexing ────────────────────────────────────────────────────────────

    def build_index(self, docs_dir: str | Path) -> int:
        """Recursively index all text docs under docs_dir. Returns chunk count."""
        docs_dir = Path(docs_dir)
        chunks, ids, metas = [], [], []

        for ext in _INDEX_EXTS:
            for path in sorted(docs_dir.rglob(f"*{ext}")):
                if any(skip in path.parts for skip in _SKIP_DIRS):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace").strip()
                except Exception:
                    continue
                if not text:
                    continue
                rel = str(path.relative_to(docs_dir))
                for i, chunk in enumerate(_split_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)):
                    chunks.append(chunk)
                    ids.append(f"{rel}::c{i}")
                    metas.append({"source": rel, "chunk": i})

        if not chunks:
            return 0

        batch = 64
        for i in range(0, len(chunks), batch):
            bc = chunks[i : i + batch]
            bi = ids[i : i + batch]
            bm = metas[i : i + batch]
            embs = self._embedder.encode(bc, show_progress_bar=False).tolist()
            self._col.upsert(ids=bi, documents=bc, embeddings=embs, metadatas=bm)

        return len(chunks)

    # ── Querying ────────────────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """Retrieve top-k context chunks, query Ollama, return answer string."""
        q_emb = self._embedder.encode([question], show_progress_bar=False).tolist()
        results = self._col.query(query_embeddings=q_emb, n_results=TOP_K, include=["documents"])
        docs = results["documents"][0] if results.get("documents") else []
        context = "\n\n---\n\n".join(docs) if docs else "(no context retrieved)"

        prompt = (
            "You are a precise scientific assistant for the PEN-COMPARE genomics research project.\n"
            "Answer the question using ONLY the provided context. "
            "Be concise — one or two sentences maximum. "
            "If the answer is a number, name, or category label, state it directly with no preamble.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        try:
            import ollama  # type: ignore[import]

            client = ollama.Client(host=OLLAMA_HOST)
            resp = client.generate(
                model=OLLAMA_MODEL,
                prompt=prompt,
                options={"num_predict": MAX_TOKENS, "temperature": 0.0},
            )
            return str(resp.get("response", "")).strip()
        except Exception as exc:
            return f"ERROR: {exc}"

    def collection_count(self) -> int:
        return self._col.count()


# ── Helpers ─────────────────────────────────────────────────────────────────


def _split_chunks(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks or [text[:3000]]
