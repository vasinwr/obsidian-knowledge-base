"""Tests for the PDF plugin."""

from pathlib import Path
from unittest.mock import patch

import pytest

from kb.models import SourceType
from kb.plugins.pdf import PdfPlugin


class TestPdfPlugin:
    def test_name(self):
        assert PdfPlugin().name == "pdf"

    def test_source_type(self):
        assert PdfPlugin().source_type == SourceType.PDF

    def test_can_handle(self):
        p = PdfPlugin()
        assert p.can_handle("paper.pdf")
        assert p.can_handle("/path/to/doc.PDF")
        assert p.can_handle("https://example.com/paper.pdf")
        assert not p.can_handle("https://example.com/page")
        assert not p.can_handle("file.md")

    @patch("pymupdf4llm.to_markdown")
    def test_ingest_local(self, mock_to_md, tmp_path: Path):
        pdf_file = tmp_path / "test-paper.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_to_md.return_value = "# Paper Title\n\nExtracted PDF content."

        doc = PdfPlugin().ingest(str(pdf_file))
        assert doc.title == "Test Paper"
        assert doc.content == "# Paper Title\n\nExtracted PDF content."
        assert doc.source_type == SourceType.PDF

    def test_ingest_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            PdfPlugin().ingest("/nonexistent/file.pdf")

    def test_extract_attachments(self, tmp_path: Path):
        pdf_file = tmp_path / "paper.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        dest = tmp_path / "attachments"
        attachments = PdfPlugin().extract_attachments(str(pdf_file), dest)
        assert attachments == ["paper.pdf"]
        assert (dest / "paper.pdf").exists()
