"""Tests for data models."""

from datetime import datetime, timezone

from kb.models import Answer, Chunk, Citation, Document, ReadStatus, SourceType


class TestReadStatus:
    def test_values(self):
        assert ReadStatus.READ.value == "read"
        assert ReadStatus.NOT_READ.value == "not_read"


class TestSourceType:
    def test_values(self):
        assert SourceType.WEB.value == "web"
        assert SourceType.PDF.value == "pdf"
        assert SourceType.TWITTER.value == "twitter"
        assert SourceType.MARKDOWN.value == "markdown"
        assert SourceType.CUSTOM.value == "custom"


class TestDocument:
    def test_defaults(self):
        doc = Document(
            id="abc",
            title="Test",
            source_url="https://example.com",
            source_type=SourceType.WEB,
            content="Hello",
        )
        assert doc.summary == ""
        assert doc.keywords == []
        assert doc.wikilinks == []
        assert doc.read_status == ReadStatus.NOT_READ
        assert doc.metadata == {}
        assert doc.attachments == []
        assert isinstance(doc.created_at, datetime)

    def test_custom_values(self, sample_document):
        assert sample_document.id == "abc123def456"
        assert sample_document.title == "Test Document"
        assert sample_document.keywords == ["testing", "example", "documentation"]


class TestChunk:
    def test_creation(self):
        chunk = Chunk(
            id="doc1::chunk::0",
            document_id="doc1",
            content="Hello world",
            index=0,
            start_char=0,
            end_char=11,
        )
        assert chunk.id == "doc1::chunk::0"
        assert chunk.index == 0


class TestAnswer:
    def test_defaults(self):
        answer = Answer(text="Some answer")
        assert answer.citations == []

    def test_with_citations(self):
        citation = Citation(
            document_title="Doc", source_url="https://x.com", chunk_text="text"
        )
        answer = Answer(text="Answer", citations=[citation])
        assert len(answer.citations) == 1
        assert answer.citations[0].document_title == "Doc"
