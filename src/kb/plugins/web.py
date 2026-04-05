"""Web/blog source plugin using trafilatura."""

from __future__ import annotations

import re

from kb.models import Document, SourceType
from kb.plugins.base import SourcePlugin
from kb.utils import content_hash, utcnow

_TWITTER_HOSTS = {"twitter.com", "x.com", "www.twitter.com", "www.x.com", "mobile.twitter.com"}


class WebPlugin(SourcePlugin):
    @property
    def name(self) -> str:
        return "web"

    @property
    def source_type(self) -> SourceType:
        return SourceType.WEB

    def can_handle(self, source: str) -> bool:
        if not re.match(r"https?://", source):
            return False
        # Exclude twitter/x.com URLs — handled by TwitterPlugin
        from urllib.parse import urlparse

        host = urlparse(source).hostname or ""
        return host not in _TWITTER_HOSTS

    def ingest(self, source: str) -> Document:
        import trafilatura

        downloaded = trafilatura.fetch_url(source)
        if downloaded is None:
            raise RuntimeError(f"Failed to fetch URL: {source}")

        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True) or ""
        if not text.strip():
            raise RuntimeError(f"No extractable text content at: {source}")

        metadata = trafilatura.extract_metadata(downloaded)
        title = (metadata.title if metadata and metadata.title else source)

        now = utcnow()
        return Document(
            id=content_hash(source),
            title=title,
            source_url=source,
            source_type=SourceType.WEB,
            content=text,
            created_at=now,
            updated_at=now,
        )
