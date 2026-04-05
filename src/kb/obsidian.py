"""Obsidian vault markdown writer — generates frontmatter + wikilinks."""

from __future__ import annotations

from pathlib import Path

from kb.models import Document
from kb.utils import format_date, sanitize_title, short_id


def write_document(doc: Document, vault_kb_dir: Path) -> Path:
    """Write a Document as an Obsidian-compatible markdown file.

    Returns the path to the written file.
    """
    vault_kb_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_title(doc.title) + ".md"
    filepath = vault_kb_dir / filename

    content = _render_markdown(doc)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def delete_document(doc: Document, vault_kb_dir: Path) -> bool:
    """Delete a document's markdown file from the vault. Returns True if deleted."""
    filename = sanitize_title(doc.title) + ".md"
    filepath = vault_kb_dir / filename
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def _render_markdown(doc: Document) -> str:
    """Render a Document to Obsidian-compatible markdown with YAML frontmatter."""
    parts: list[str] = []

    # YAML frontmatter
    parts.append("---")
    parts.append(f'title: "{_escape_yaml(doc.title)}"')
    if doc.source_url:
        parts.append(f'source_url: "{doc.source_url}"')
    parts.append(f"source_type: {doc.source_type.value}")
    parts.append(f"read_status: {doc.read_status.value}")
    parts.append(f"created: {format_date(doc.created_at)}")
    parts.append(f"updated: {format_date(doc.updated_at)}")
    parts.append(f"doc_id: {short_id(doc.id)}")
    if doc.keywords:
        parts.append("tags:")
        for kw in doc.keywords:
            parts.append(f"  - {_tag_format(kw)}")
    if doc.wikilinks:
        parts.append("related:")
        for link in doc.wikilinks:
            parts.append(f'  - "[[{link}]]"')
    parts.append("---")
    parts.append("")

    # Summary
    if doc.summary:
        parts.append("## Summary")
        parts.append(doc.summary)
        parts.append("")

    # Source link
    if doc.source_url:
        parts.append("## Source")
        parts.append(f"[Original]({doc.source_url})")
        parts.append("")

    # Related (wikilinks in body)
    if doc.wikilinks:
        parts.append("## Related")
        parts.append(" | ".join(f"[[{link}]]" for link in doc.wikilinks))
        parts.append("")

    # Keywords as tags
    if doc.keywords:
        parts.append("## Keywords")
        parts.append(" ".join(f"#{_tag_format(kw)}" for kw in doc.keywords))
        parts.append("")

    # Attachments
    if doc.attachments:
        parts.append("## Attachments")
        for att in doc.attachments:
            parts.append(f"- ![[{att}]]")
        parts.append("")

    # Full content in collapsible callout
    if doc.content:
        parts.append("## Full Content")
        parts.append("> [!note]- Expand full text")
        for line in doc.content.splitlines():
            parts.append(f"> {line}" if line.strip() else ">")
        parts.append("")

    return "\n".join(parts)


def _escape_yaml(text: str) -> str:
    """Escape characters problematic in YAML strings."""
    return text.replace('"', '\\"')


def _tag_format(keyword: str) -> str:
    """Format a keyword as an Obsidian tag (lowercase, hyphens, no spaces)."""
    return keyword.lower().replace(" ", "-").replace("_", "-")
