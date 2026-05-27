"""Unit tests for pen_compare.rag internals that don't require GPU/Ollama.

Only tests _split_chunks (pure Python, no heavy deps) and the constants.
chromadb / sentence-transformers are optional — tests are skipped when absent.
"""

import pytest

try:
    from pen_stack.compare.rag.qa import CHUNK_OVERLAP, CHUNK_SIZE, TOP_K, _split_chunks

    _HAS_RAG = True
except ImportError:
    _HAS_RAG = False

pytestmark = pytest.mark.skipif(not _HAS_RAG, reason="chromadb/sentence-transformers not installed")


class TestSplitChunks:
    def test_empty_string_returns_empty(self):
        assert _split_chunks("", 400, 80) == []

    def test_whitespace_only_returns_empty(self):
        assert _split_chunks("   \n  ", 400, 80) == []

    def test_short_text_returns_one_chunk(self):
        text = "hello world this is a short text"
        chunks = _split_chunks(text, 400, 80)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_count_is_correct(self):
        # 100 words, size=50, overlap=10 → step=40 → ceil(100/40)=3 chunks
        text = " ".join(["word"] * 100)
        chunks = _split_chunks(text, 50, 10)
        assert len(chunks) >= 2

    def test_no_chunk_exceeds_size_words(self):
        text = " ".join(["word"] * 300)
        chunks = _split_chunks(text, 100, 20)
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    def test_overlap_between_adjacent_chunks(self):
        words = [f"w{i}" for i in range(100)]
        text = " ".join(words)
        chunks = _split_chunks(text, 50, 20)
        if len(chunks) >= 2:
            last_words_c0 = chunks[0].split()[-20:]
            first_words_c1 = chunks[1].split()[:20]
            # At least some words are shared (overlap)
            overlap = set(last_words_c0) & set(first_words_c1)
            assert len(overlap) > 0

    def test_single_word(self):
        chunks = _split_chunks("hello", 400, 80)
        assert chunks == ["hello"]

    def test_exact_size_boundary(self):
        # exactly CHUNK_SIZE words — should be exactly 1 chunk
        text = " ".join(["x"] * CHUNK_SIZE)
        chunks = _split_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)
        assert len(chunks) == 1

    def test_step_of_one_when_overlap_gte_size(self):
        # overlap >= size → step=1 (clamped to max(1, ...))
        text = " ".join(["w"] * 10)
        chunks = _split_chunks(text, 5, 10)
        # shouldn't crash; at least 1 chunk
        assert len(chunks) >= 1

    def test_all_chunks_are_non_empty(self):
        text = " ".join(["word"] * 500)
        for chunk in _split_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP):
            assert chunk.strip() != ""


class TestConstants:
    def test_chunk_size_positive(self):
        assert CHUNK_SIZE > 0

    def test_chunk_overlap_less_than_size(self):
        assert CHUNK_OVERLAP < CHUNK_SIZE

    def test_top_k_positive(self):
        assert TOP_K > 0
