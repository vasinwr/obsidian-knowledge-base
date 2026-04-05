"""Abstract base class for source plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from kb.models import Document, SourceType


class SourcePlugin(ABC):
    """Base class that all source plugins must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier (e.g. 'web', 'pdf')."""

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """The SourceType enum value this plugin handles."""

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Return True if this plugin can ingest *source*."""

    @abstractmethod
    def ingest(self, source: str) -> Document:
        """Fetch and parse *source*, returning a Document.

        The returned Document should have id, title, source_url, source_type,
        and content populated.  summary, keywords, and wikilinks are left
        empty for the pipeline to fill in via LLM.
        """

    def extract_attachments(self, source: str, dest_dir: Path) -> list[str]:
        """Optionally extract attachments to *dest_dir*.

        Returns a list of file paths relative to *dest_dir*.
        Default implementation returns an empty list.
        """
        return []
