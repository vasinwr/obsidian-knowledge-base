"""Tests for the web plugin."""

from unittest.mock import MagicMock, patch

import pytest

from kb.models import SourceType
from kb.plugins.web import WebPlugin


class TestWebPlugin:
    def test_name(self):
        assert WebPlugin().name == "web"

    def test_source_type(self):
        assert WebPlugin().source_type == SourceType.WEB

    def test_can_handle_http(self):
        p = WebPlugin()
        assert p.can_handle("https://example.com")
        assert p.can_handle("http://example.com/page")
        assert p.can_handle("https://paulgraham.com/greatwork.html")

    def test_cannot_handle_twitter(self):
        p = WebPlugin()
        assert not p.can_handle("https://twitter.com/user/status/123")
        assert not p.can_handle("https://x.com/user/status/123")

    def test_cannot_handle_file(self):
        p = WebPlugin()
        assert not p.can_handle("/path/to/file.md")
        assert not p.can_handle("file.pdf")

    @patch("trafilatura.extract_metadata")
    @patch("trafilatura.extract")
    @patch("trafilatura.fetch_url")
    def test_ingest(self, mock_fetch, mock_extract, mock_meta):
        mock_fetch.return_value = "<html>content</html>"
        mock_extract.return_value = "Extracted text content"
        meta = MagicMock()
        meta.title = "Test Page"
        mock_meta.return_value = meta

        doc = WebPlugin().ingest("https://example.com/page")
        assert doc.title == "Test Page"
        assert doc.content == "Extracted text content"
        assert doc.source_type == SourceType.WEB
        assert doc.source_url == "https://example.com/page"

    @patch("trafilatura.fetch_url")
    def test_ingest_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = None
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            WebPlugin().ingest("https://example.com/bad")

    @patch("trafilatura.extract")
    @patch("trafilatura.fetch_url")
    def test_ingest_empty_content(self, mock_fetch, mock_extract):
        mock_fetch.return_value = "<html></html>"
        mock_extract.return_value = ""
        with pytest.raises(RuntimeError, match="No extractable text"):
            WebPlugin().ingest("https://example.com/empty")
