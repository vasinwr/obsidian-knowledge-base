"""Tests for Obsidian markdown writer."""

from pathlib import Path

from kb.models import Document, ReadStatus, SourceType
from kb.obsidian import delete_document, write_document


class TestObsidian:
    def test_write_creates_file(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        assert path.exists()
        assert path.name == "Test Document.md"

    def test_frontmatter(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert content.startswith("---\n")
        assert 'title: "Test Document"' in content
        assert "source_type: web" in content
        assert "read_status: not_read" in content
        assert "doc_id: abc123de" in content

    def test_tags_in_frontmatter(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "  - testing" in content
        assert "  - example" in content

    def test_summary_section(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "## Summary" in content
        assert "A test document summary." in content

    def test_source_link(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "[Original](https://example.com/test)" in content

    def test_wikilinks(self, sample_document: Document, tmp_dir: Path):
        sample_document.wikilinks = ["Doc A", "Doc B"]
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "[[Doc A]]" in content
        assert "[[Doc B]]" in content

    def test_keywords_as_tags(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "#testing" in content
        assert "#example" in content

    def test_collapsible_content(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "> [!note]- Expand full text" in content
        assert "> This is a test document" in content

    def test_attachments(self, sample_document: Document, tmp_dir: Path):
        sample_document.attachments = ["paper.pdf"]
        kb_dir = tmp_dir / "Knowledge Base"
        path = write_document(sample_document, kb_dir)
        content = path.read_text()
        assert "![[paper.pdf]]" in content

    def test_delete_document(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        write_document(sample_document, kb_dir)
        assert delete_document(sample_document, kb_dir)
        assert not (kb_dir / "Test Document.md").exists()

    def test_delete_nonexistent(self, sample_document: Document, tmp_dir: Path):
        kb_dir = tmp_dir / "Knowledge Base"
        assert not delete_document(sample_document, kb_dir)
