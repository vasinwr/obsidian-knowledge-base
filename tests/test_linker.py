"""Tests for LLM-powered wikilink generation."""

from unittest.mock import MagicMock, patch

from kb.linker import _parse_title_list, find_links
from kb.models import Document, SourceType


class TestParseTitle:
    def test_json_array(self):
        titles = _parse_title_list('["Doc A", "Doc B"]', {"Doc A", "Doc B", "Doc C"})
        assert titles == ["Doc A", "Doc B"]

    def test_json_with_surrounding_text(self):
        resp = 'Here are the related: ["Doc A", "Doc B"]'
        titles = _parse_title_list(resp, {"Doc A", "Doc B"})
        assert titles == ["Doc A", "Doc B"]

    def test_filters_invalid(self):
        titles = _parse_title_list('["Doc A", "Unknown"]', {"Doc A", "Doc B"})
        assert titles == ["Doc A"]

    def test_fallback_matching(self):
        titles = _parse_title_list("Doc A is related", {"Doc A", "Doc B"})
        assert "Doc A" in titles

    def test_empty(self):
        titles = _parse_title_list("[]", {"Doc A"})
        assert titles == []


class TestFindLinks:
    def test_no_candidates(self, db, mock_llm):
        doc = Document(
            id="doc1",
            title="Test",
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content="Content",
            summary="Summary",
            keywords=["testing"],
        )

        vs = MagicMock()
        vs.search.return_value = []

        with patch("kb.linker.embed_text", return_value=[0.1] * 384):
            links = find_links(doc, db, vs, mock_llm)
        assert links == []

    def test_with_candidates(self, db, mock_llm):
        # Store an existing document
        existing = Document(
            id="doc_existing",
            title="Related Doc",
            source_url="https://example.com/related",
            source_type=SourceType.WEB,
            content="Related content",
            keywords=["testing"],
        )
        db.upsert_document(existing)

        doc = Document(
            id="doc_new",
            title="New Doc",
            source_url="https://example.com/new",
            source_type=SourceType.WEB,
            content="New content about testing",
            summary="Summary about testing",
            keywords=["testing"],
        )

        vs = MagicMock()
        vs.search.return_value = [
            {
                "id": "doc_existing::chunk::0",
                "document_id": "doc_existing",
                "content": "Related content",
                "score": 0.9,
                "metadata": {},
            }
        ]

        mock_llm.complete.return_value = '["Related Doc"]'

        with patch("kb.linker.embed_text", return_value=[0.1] * 384):
            links = find_links(doc, db, vs, mock_llm)
        assert "Related Doc" in links
