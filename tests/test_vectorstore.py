"""Tests for ChromaDB vector store wrapper."""

from pathlib import Path

import pytest

from kb.models import Chunk
from kb.vectorstore import VectorStore


@pytest.fixture
def vs(tmp_path: Path) -> VectorStore:
    return VectorStore(tmp_path / "chroma")


def _make_chunks(doc_id: str, n: int) -> list[Chunk]:
    return [
        Chunk(
            id=f"{doc_id}::chunk::{i}",
            document_id=doc_id,
            content=f"Chunk content {i} for {doc_id}",
            index=i,
            start_char=i * 100,
            end_char=(i + 1) * 100,
        )
        for i in range(n)
    ]


def _fake_embeddings(n: int, dim: int = 384) -> list[list[float]]:
    """Generate simple fake embeddings."""
    import random
    random.seed(42)
    return [[random.random() for _ in range(dim)] for _ in range(n)]


class TestVectorStore:
    def test_upsert_and_count(self, vs: VectorStore):
        chunks = _make_chunks("doc1", 3)
        embeddings = _fake_embeddings(3)
        vs.upsert_chunks(chunks, embeddings)
        assert vs.count() == 3

    def test_upsert_idempotent(self, vs: VectorStore):
        chunks = _make_chunks("doc1", 3)
        embeddings = _fake_embeddings(3)
        vs.upsert_chunks(chunks, embeddings)
        vs.upsert_chunks(chunks, embeddings)
        assert vs.count() == 3

    def test_search(self, vs: VectorStore):
        chunks = _make_chunks("doc1", 3)
        embeddings = _fake_embeddings(3)
        vs.upsert_chunks(chunks, embeddings)

        results = vs.search(embeddings[0], n_results=2)
        assert len(results) == 2
        assert results[0]["document_id"] == "doc1"
        assert "score" in results[0]

    def test_search_exclude_doc(self, vs: VectorStore):
        chunks1 = _make_chunks("doc1", 2)
        chunks2 = _make_chunks("doc2", 2)
        emb1 = _fake_embeddings(2)
        emb2 = _fake_embeddings(2)
        vs.upsert_chunks(chunks1, emb1)
        vs.upsert_chunks(chunks2, emb2)

        results = vs.search(emb1[0], n_results=4, exclude_doc_id="doc1")
        for r in results:
            assert r["document_id"] != "doc1"

    def test_delete_by_document(self, vs: VectorStore):
        chunks = _make_chunks("doc1", 3)
        embeddings = _fake_embeddings(3)
        vs.upsert_chunks(chunks, embeddings)
        assert vs.count() == 3
        vs.delete_by_document("doc1")
        assert vs.count() == 0

    def test_empty_upsert(self, vs: VectorStore):
        vs.upsert_chunks([], [])
        assert vs.count() == 0
