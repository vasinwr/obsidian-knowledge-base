"""Tests for RAG Q&A engine."""

from unittest.mock import MagicMock, patch

from kb.models import Document, SourceType
from kb.rag import ask


class TestRAG:
    def test_ask_no_results(self, db, mock_llm):
        vs = MagicMock()
        vs.search.return_value = []
        answer = ask("What is this?", db, vs, mock_llm)
        assert "No relevant documents" in answer.text
        assert answer.citations == []

    def test_ask_with_results(self, db, mock_llm):
        # Set up a document in the DB
        doc = Document(
            id="doc1",
            title="Test Doc",
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content="Some content about testing.",
        )
        db.upsert_document(doc)

        # Mock vector store to return matching chunks
        vs = MagicMock()
        vs.search.return_value = [
            {
                "id": "doc1::chunk::0",
                "document_id": "doc1",
                "content": "Some content about testing.",
                "score": 0.95,
                "metadata": {"index": 0, "start_char": 0, "end_char": 27},
            }
        ]

        # Mock LLM to return a cited answer
        mock_llm.complete.return_value = (
            "Based on the source, testing is important [Source 1]."
        )

        with patch("kb.rag.embed_text", return_value=[0.1] * 384):
            answer = ask("What about testing?", db, vs, mock_llm)

        assert "testing" in answer.text
        assert len(answer.citations) == 1
        assert answer.citations[0].document_title == "Test Doc"

    def test_ask_uncited_sources_excluded(self, db, mock_llm):
        doc = Document(
            id="doc1",
            title="Test Doc",
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content="Content.",
        )
        db.upsert_document(doc)

        vs = MagicMock()
        vs.search.return_value = [
            {
                "id": "doc1::chunk::0",
                "document_id": "doc1",
                "content": "Content.",
                "score": 0.9,
                "metadata": {},
            }
        ]
        # LLM doesn't cite any source
        mock_llm.complete.return_value = "I don't know."

        with patch("kb.rag.embed_text", return_value=[0.1] * 384):
            answer = ask("Unknown?", db, vs, mock_llm)

        assert answer.citations == []
