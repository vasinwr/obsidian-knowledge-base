"""Core data models for the knowledge base."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ReadStatus(Enum):
    READ = "read"
    NOT_READ = "not_read"


class SourceType(Enum):
    WEB = "web"
    PDF = "pdf"
    TWITTER = "twitter"
    MARKDOWN = "markdown"
    CUSTOM = "custom"


@dataclass
class Document:
    id: str  # SHA-256 of source URL or content
    title: str
    source_url: str
    source_type: SourceType
    content: str
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)  # titles of linked docs
    read_status: ReadStatus = ReadStatus.NOT_READ
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    id: str  # "{doc_id}::chunk::{index}"
    document_id: str
    content: str
    index: int
    start_char: int
    end_char: int


@dataclass
class SearchResult:
    document: Document
    chunk: Chunk | None = None
    score: float = 0.0
    highlight: str = ""


@dataclass
class Citation:
    document_title: str
    source_url: str
    chunk_text: str


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
