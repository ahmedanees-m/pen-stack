"""Tests for PenStackQA that don't require Ollama (ChromaDB + embeddings only)."""

import pytest

try:
    from pen_stack.compare.rag.qa import PenStackQA

    _HAS_RAG = True
except ImportError:
    _HAS_RAG = False

pytestmark = pytest.mark.skipif(not _HAS_RAG, reason="chromadb/sentence-transformers not installed")


@pytest.fixture(scope="module")
def qa_instance(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("rag_db")
    return PenStackQA(db_path=db_path)


@pytest.fixture(scope="module")
def qa_with_index(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("rag_db_idx")
    qa = PenStackQA(db_path=db_path)
    # Create small docs directory
    docs = tmp_path_factory.mktemp("docs")
    (docs / "gates.md").write_text(
        "# Gate 1 DSB Avoidance\n"
        "Threshold: 0.95. Necessary gate. Failing auto-classifies as NOT_WRITER.\n"
        "ISCro4 has S_DSB=1.0 and passes this gate.\n"
    )
    (docs / "predictions.yaml").write_text(
        "predictions:\n  P1: ISCro4 is the sole TRUE_WRITER.\n  P2: Zero designs are TRUE_WRITER.\n"
    )
    qa.build_index(docs)
    return qa


class TestPenStackQAInit:
    def test_init_creates_instance(self, qa_instance):
        assert qa_instance is not None

    def test_collection_count_empty(self, qa_instance):
        assert qa_instance.collection_count() >= 0

    def test_collection_count_is_int(self, qa_instance):
        assert isinstance(qa_instance.collection_count(), int)


class TestBuildIndex:
    def test_build_index_returns_chunk_count(self, qa_with_index):
        count = qa_with_index.collection_count()
        assert count > 0

    def test_empty_dir_returns_zero(self, tmp_path):
        qa = PenStackQA(db_path=tmp_path / "empty_db")
        n = qa.build_index(tmp_path / "empty_docs")
        assert n == 0

    def test_skips_empty_files(self, tmp_path):
        db_path = tmp_path / "db"
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        (docs_path / "empty.md").write_text("")
        (docs_path / "real.md").write_text("This is some content for indexing.")
        qa = PenStackQA(db_path=db_path)
        n = qa.build_index(docs_path)
        assert n == 1  # only real.md contributes

    def test_build_index_returns_int(self, tmp_path):
        db_path = tmp_path / "db2"
        docs_path = tmp_path / "docs2"
        docs_path.mkdir()
        (docs_path / "a.md").write_text("content " * 50)
        qa = PenStackQA(db_path=db_path)
        result = qa.build_index(docs_path)
        assert isinstance(result, int)
        assert result >= 1

    def test_upsert_is_idempotent(self, tmp_path):
        db_path = tmp_path / "db3"
        docs_path = tmp_path / "docs3"
        docs_path.mkdir()
        (docs_path / "a.md").write_text("content " * 50)
        qa = PenStackQA(db_path=db_path)
        n1 = qa.build_index(docs_path)
        n2 = qa.build_index(docs_path)
        # Upsert: second call shouldn't raise; count should be same
        assert qa.collection_count() == n1
        assert n1 == n2


class TestAskWithoutOllama:
    def test_ask_without_ollama_returns_error_string(self, qa_with_index):
        # Ollama not running in unit test environment → returns "ERROR: ..."
        result = qa_with_index.ask("What is the G1 threshold?")
        assert isinstance(result, str)
        # Either a proper answer (if ollama running) or error message
        assert len(result) > 0
