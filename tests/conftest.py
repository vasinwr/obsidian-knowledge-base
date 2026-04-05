"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kb.config import Config
from kb.database import Database
from kb.models import Document, ReadStatus, SourceType


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config(tmp_path: Path) -> Config:
    vault = tmp_path / "vault"
    vault.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    return Config(
        vault_path=str(vault),
        vault_subfolder="Knowledge Base",
        data_dir=data,
    )


@pytest.fixture
def db(config: Config) -> Database:
    database = Database(config.sqlite_path)
    yield database
    database.close()


@pytest.fixture
def sample_document() -> Document:
    return Document(
        id="abc123def456",
        title="Test Document",
        source_url="https://example.com/test",
        source_type=SourceType.WEB,
        content="This is a test document with some content.\n\nIt has multiple paragraphs.\n\nAnd a third one.",
        summary="A test document summary.",
        keywords=["testing", "example", "documentation"],
        wikilinks=[],
        read_status=ReadStatus.NOT_READ,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """A mock LLM provider that returns canned responses."""
    llm = MagicMock()
    llm.complete.return_value = "Mock LLM response"
    return llm
