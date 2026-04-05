"""Local markdown / plain-text file source plugin."""

from __future__ import annotations

from pathlib import Path

from kb.models import Document, SourceType
from kb.plugins.base import SourcePlugin
from kb.utils import content_hash, utcnow

_EXTENSIONS = {".md", ".markdown", ".txt"}


class MarkdownPlugin(SourcePlugin):
    @property
    def name(self) -> str:
        return "markdown"

    @property
    def source_type(self) -> SourceType:
        return SourceType.MARKDOWN

    def can_handle(self, source: str) -> bool:
        if source.startswith("http"):
            return False
        return Path(source).suffix.lower() in _EXTENSIONS

    def ingest(self, source: str) -> Document:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {source}")

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise RuntimeError(f"File is empty: {source}")

        # Use filename (without extension) as title
        title = path.stem.replace("-", " ").replace("_", " ").title()

        now = utcnow()
        return Document(
            id=content_hash(str(path.resolve())),
            title=title,
            source_url=str(path.resolve()),
            source_type=SourceType.MARKDOWN,
            content=content,
            created_at=now,
            updated_at=now,
        )
