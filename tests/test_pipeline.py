"""Tests for ingestion pipeline with mock LLM."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kb.config import Config
from kb.database import Database
from kb.models import Document, SourceType
from kb.pipeline import ingest


@pytest.fixture
def pipeline_config(tmp_path: Path) -> Config:
    vault = tmp_path / "vault"
    vault.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    (data / "chroma").mkdir()
    (vault / "Knowledge Base").mkdir()
    (vault / "attachments").mkdir()
    return Config(vault_path=str(vault), data_dir=data)


@pytest.fixture
def pipeline_db(pipeline_config: Config) -> Database:
    database = Database(pipeline_config.sqlite_path)
    yield database
    database.close()


class TestPipeline:
    @patch("kb.pipeline.embed_texts")
    @patch("kb.pipeline.find_links")
    def test_ingest_markdown_file(
        self, mock_find_links, mock_embed_texts, pipeline_config, pipeline_db, mock_llm, tmp_path
    ):
        # Create a test markdown file
        md_file = tmp_path / "test_note.md"
        md_file.write_text("# Test Note\n\nThis is a test note with some content.")

        mock_embed_texts.return_value = [[0.1] * 384]
        mock_find_links.return_value = []
        mock_llm.complete.side_effect = [
            "This is a summary of the test note.",  # summarize
            "testing, notes, markdown",  # keywords
        ]

        # Register plugins
        from kb.plugins import load_builtin_plugins, reset_registry
        reset_registry()
        load_builtin_plugins()

        vs = MagicMock()

        doc = ingest(str(md_file), pipeline_config, pipeline_db, vs, mock_llm)

        assert doc.title == "Test Note"
        assert doc.summary == "This is a summary of the test note."
        assert "testing" in doc.keywords
        assert pipeline_db.document_exists(doc.id)

        # Verify vault page was written
        vault_page = pipeline_config.vault_kb_dir / "Test Note.md"
        assert vault_page.exists()

    @patch("kb.pipeline.embed_texts")
    @patch("kb.pipeline.find_links")
    def test_dedup_skips(
        self, mock_find_links, mock_embed_texts, pipeline_config, pipeline_db, mock_llm, tmp_path
    ):
        md_file = tmp_path / "test.md"
        md_file.write_text("Content here")

        mock_embed_texts.return_value = [[0.1] * 384]
        mock_find_links.return_value = []
        mock_llm.complete.side_effect = ["Summary", "keyword1, keyword2"]

        from kb.plugins import load_builtin_plugins, reset_registry
        reset_registry()
        load_builtin_plugins()

        vs = MagicMock()

        # First ingest
        doc1 = ingest(str(md_file), pipeline_config, pipeline_db, vs, mock_llm)

        # Second ingest without force — should skip (dedup)
        mock_llm.complete.side_effect = None  # Won't be called
        doc2 = ingest(str(md_file), pipeline_config, pipeline_db, vs, mock_llm)
        assert doc2.id == doc1.id

    def test_ingest_unknown_source(self, pipeline_config, pipeline_db, mock_llm):
        from kb.plugins import load_builtin_plugins, reset_registry
        reset_registry()
        load_builtin_plugins()

        vs = MagicMock()

        with pytest.raises(ValueError, match="No plugin"):
            ingest("unknown://source", pipeline_config, pipeline_db, vs, mock_llm)
