"""Tests for the Twitter plugin."""

from unittest.mock import patch

import pytest

from kb.models import SourceType
from kb.plugins.twitter import TwitterPlugin


class TestTwitterPlugin:
    def test_name(self):
        assert TwitterPlugin().name == "twitter"

    def test_source_type(self):
        assert TwitterPlugin().source_type == SourceType.TWITTER

    def test_can_handle(self):
        p = TwitterPlugin()
        assert p.can_handle("https://twitter.com/user/status/123")
        assert p.can_handle("https://x.com/user/status/456")
        assert not p.can_handle("https://example.com")
        assert not p.can_handle("file.md")

    @patch.dict("os.environ", {"TWITTER_BEARER_TOKEN": ""})
    @patch("trafilatura.extract")
    @patch("trafilatura.fetch_url")
    def test_ingest_trafilatura_fallback(self, mock_fetch, mock_extract):
        mock_fetch.return_value = "<html>tweet</html>"
        mock_extract.return_value = "Tweet text content here"

        doc = TwitterPlugin().ingest("https://x.com/user/status/123")
        assert doc.source_type == SourceType.TWITTER
        assert doc.content == "Tweet text content here"

    @patch.dict("os.environ", {"TWITTER_BEARER_TOKEN": ""})
    @patch("trafilatura.fetch_url")
    def test_ingest_fetch_failure(self, mock_fetch):
        mock_fetch.return_value = None
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            TwitterPlugin().ingest("https://twitter.com/user/status/123")
