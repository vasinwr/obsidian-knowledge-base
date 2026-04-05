"""Utility helpers — hashing, slugification, date formatting."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone


def content_hash(text: str) -> str:
    """Return a deterministic SHA-256 hex digest for *text*."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(text: str, max_length: int = 80) -> str:
    """Convert *text* to a filesystem-safe slug.

    Lowercases, strips accents, replaces non-alphanumerics with hyphens,
    and truncates to *max_length* characters.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_length]


def sanitize_title(title: str) -> str:
    """Remove characters illegal in filenames while keeping readability."""
    illegal = r'[<>:"/\\|?*]'
    return re.sub(illegal, "", title).strip()


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_date(dt: datetime) -> str:
    """Format a datetime as an ISO-8601 date string (YYYY-MM-DD)."""
    return dt.strftime("%Y-%m-%d")


def short_id(doc_id: str) -> str:
    """Return the first 8 characters of a document ID for display."""
    return doc_id[:8]
