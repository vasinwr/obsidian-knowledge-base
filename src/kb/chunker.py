"""Paragraph-aware text chunking with overlap and character offset tracking."""

from __future__ import annotations

from kb.models import Chunk


def chunk_text(
    document_id: str,
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split *text* into overlapping chunks, respecting paragraph boundaries.

    Returns a list of :class:`Chunk` objects with character offsets.
    """
    if not text.strip():
        return []

    paragraphs = _split_paragraphs(text)
    chunks: list[Chunk] = []
    current_text = ""
    current_start = 0
    para_cursor = 0  # character position in the original text
    index = 0

    for para in paragraphs:
        para_len = len(para)

        if current_text and len(current_text) + len(para) + 1 > chunk_size:
            # Emit the current chunk
            chunk = Chunk(
                id=f"{document_id}::chunk::{index}",
                document_id=document_id,
                content=current_text.strip(),
                index=index,
                start_char=current_start,
                end_char=current_start + len(current_text.strip()),
            )
            chunks.append(chunk)
            index += 1

            # Overlap: keep the tail of the current text
            if overlap > 0 and len(current_text) > overlap:
                tail = current_text[-overlap:]
                current_start = current_start + len(current_text) - overlap
                current_text = tail
            else:
                current_start = para_cursor
                current_text = ""

        if current_text:
            current_text += "\n" + para
        else:
            current_start = para_cursor
            current_text = para

        # If a single paragraph exceeds chunk_size, force-split it
        while len(current_text) > chunk_size:
            slice_text = current_text[:chunk_size].strip()
            chunk = Chunk(
                id=f"{document_id}::chunk::{index}",
                document_id=document_id,
                content=slice_text,
                index=index,
                start_char=current_start,
                end_char=current_start + len(slice_text),
            )
            chunks.append(chunk)
            index += 1

            if overlap > 0:
                remaining = current_text[chunk_size - overlap:]
                current_start += chunk_size - overlap
            else:
                remaining = current_text[chunk_size:]
                current_start += chunk_size
            current_text = remaining

        para_cursor += para_len + 1  # +1 for the newline between paragraphs

    # Emit any remaining text
    if current_text.strip():
        chunk = Chunk(
            id=f"{document_id}::chunk::{index}",
            document_id=document_id,
            content=current_text.strip(),
            index=index,
            start_char=current_start,
            end_char=current_start + len(current_text.strip()),
        )
        chunks.append(chunk)

    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """Split text on blank lines (double newlines) or single newlines.

    Preserves non-empty paragraphs.
    """
    # Split on double-newlines first (standard paragraphs)
    raw = text.split("\n\n")
    paragraphs: list[str] = []
    for block in raw:
        stripped = block.strip()
        if stripped:
            paragraphs.append(stripped)
    return paragraphs
