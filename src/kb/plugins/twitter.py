"""Twitter/X source plugin with tweepy API + trafilatura fallback."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from kb.models import Document, SourceType
from kb.plugins.base import SourcePlugin
from kb.utils import content_hash, utcnow

_TWITTER_HOSTS = {"twitter.com", "x.com", "www.twitter.com", "www.x.com", "mobile.twitter.com"}
_TWEET_ID_RE = re.compile(r"/status/(\d+)")


class TwitterPlugin(SourcePlugin):
    @property
    def name(self) -> str:
        return "twitter"

    @property
    def source_type(self) -> SourceType:
        return SourceType.TWITTER

    def can_handle(self, source: str) -> bool:
        if not re.match(r"https?://", source):
            return False
        host = urlparse(source).hostname or ""
        return host in _TWITTER_HOSTS

    def ingest(self, source: str) -> Document:
        # Try tweepy first if bearer token is available
        bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
        if bearer:
            try:
                return self._ingest_via_api(source, bearer)
            except Exception:
                pass  # Fall through to trafilatura

        return self._ingest_via_trafilatura(source)

    def _ingest_via_api(self, source: str, bearer_token: str) -> Document:
        import tweepy

        match = _TWEET_ID_RE.search(source)
        if not match:
            raise ValueError(f"Could not extract tweet ID from: {source}")
        tweet_id = match.group(1)

        client = tweepy.Client(bearer_token=bearer_token)
        resp = client.get_tweet(
            tweet_id,
            tweet_fields=["created_at", "author_id", "text"],
            user_fields=["username", "name"],
            expansions=["author_id"],
        )
        if resp.data is None:
            raise RuntimeError(f"Tweet not found: {source}")

        tweet = resp.data
        users = {u.id: u for u in (resp.includes.get("users", []))}
        author = users.get(tweet.author_id)
        author_name = f"@{author.username}" if author else "Unknown"

        title = f"Tweet by {author_name}"
        content = tweet.text

        now = utcnow()
        return Document(
            id=content_hash(source),
            title=title,
            source_url=source,
            source_type=SourceType.TWITTER,
            content=content,
            created_at=now,
            updated_at=now,
            metadata={"author": author_name, "tweet_id": tweet_id},
        )

    def _ingest_via_trafilatura(self, source: str) -> Document:
        import trafilatura

        downloaded = trafilatura.fetch_url(source)
        if downloaded is None:
            raise RuntimeError(f"Failed to fetch tweet page: {source}")

        text = trafilatura.extract(downloaded) or ""
        if not text.strip():
            raise RuntimeError(f"No extractable text from tweet: {source}")

        title = f"Tweet — {source.split('/')[-1]}"

        now = utcnow()
        return Document(
            id=content_hash(source),
            title=title,
            source_url=source,
            source_type=SourceType.TWITTER,
            content=text,
            created_at=now,
            updated_at=now,
        )
