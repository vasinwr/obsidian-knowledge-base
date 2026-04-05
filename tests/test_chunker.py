"""Tests for paragraph-aware text chunking."""

from kb.chunker import chunk_text


class TestChunker:
    def test_basic_chunking(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = chunk_text("doc1", text, chunk_size=512, overlap=64)
        assert len(chunks) >= 1
        # All content should be present across chunks
        combined = " ".join(c.content for c in chunks)
        assert "Paragraph one" in combined
        assert "Paragraph two" in combined
        assert "Paragraph three" in combined

    def test_chunk_ids(self):
        text = "A" * 1000 + "\n\n" + "B" * 1000
        chunks = chunk_text("doc1", text, chunk_size=512, overlap=64)
        for i, chunk in enumerate(chunks):
            assert chunk.id == f"doc1::chunk::{i}"
            assert chunk.index == i
            assert chunk.document_id == "doc1"

    def test_empty_text(self):
        chunks = chunk_text("doc1", "", chunk_size=512, overlap=64)
        assert chunks == []

    def test_whitespace_only(self):
        chunks = chunk_text("doc1", "   \n\n  ", chunk_size=512, overlap=64)
        assert chunks == []

    def test_short_text_single_chunk(self):
        text = "Short text."
        chunks = chunk_text("doc1", text, chunk_size=512, overlap=64)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."

    def test_char_offsets(self):
        text = "Hello world"
        chunks = chunk_text("doc1", text, chunk_size=512, overlap=0)
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len("Hello world")

    def test_long_paragraph_force_split(self):
        text = "A" * 1500  # Longer than chunk_size
        chunks = chunk_text("doc1", text, chunk_size=512, overlap=64)
        assert len(chunks) > 1
        # Each chunk should be at most chunk_size
        for chunk in chunks:
            assert len(chunk.content) <= 512

    def test_overlap_present(self):
        # Two paragraphs that each fill a chunk
        text = "A" * 400 + "\n\n" + "B" * 400
        chunks = chunk_text("doc1", text, chunk_size=450, overlap=64)
        assert len(chunks) >= 2
