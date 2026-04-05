"""Ingestion pipeline orchestration — 10-stage sequential pipeline."""

from __future__ import annotations

from rich.console import Console

from kb.chunker import chunk_text
from kb.config import Config
from kb.database import Database
from kb.embeddings import embed_texts
from kb.linker import find_links
from kb.llm import LLMProvider
from kb.models import Document
from kb.obsidian import write_document
from kb.plugins import get_plugin_for
from kb.utils import utcnow
from kb.vectorstore import VectorStore

console = Console()

SUMMARIZE_PROMPT = """Summarize the following document in 2-3 concise paragraphs. Focus on the key ideas, arguments, and conclusions.

Document title: {title}

Document content:
{content}

Summary:"""

KEYWORDS_PROMPT = """Extract 5-10 topic keywords from the following document. Return them as a comma-separated list. Keywords should be specific, descriptive, and useful for categorization.

Document title: {title}

Document content (excerpt):
{content}

Keywords (comma-separated):"""


def ingest(
    source: str,
    config: Config,
    db: Database,
    vectorstore: VectorStore,
    llm: LLMProvider,
    *,
    force: bool = False,
) -> Document:
    """Run the full 10-stage ingestion pipeline for a single source.

    Stages: RESOLVE → EXTRACT → DEDUP → ATTACHMENTS → SUMMARIZE →
            KEYWORDS → CHUNK → EMBED → LINK → WRITE
    """
    # 1. RESOLVE — find matching plugin
    console.print(f"[dim]RESOLVE[/dim] Finding plugin for: {source}")
    plugin = get_plugin_for(source)
    if plugin is None:
        raise ValueError(f"No plugin can handle source: {source}")
    console.print(f"  → Using plugin: [bold]{plugin.name}[/bold]")

    # 2. EXTRACT — plugin fetches and parses content
    console.print("[dim]EXTRACT[/dim] Fetching and parsing content...")
    doc = plugin.ingest(source)
    console.print(f"  → Title: [bold]{doc.title}[/bold] ({len(doc.content)} chars)")

    # 3. DEDUP — check if already ingested
    console.print("[dim]DEDUP[/dim] Checking for duplicates...")
    if db.document_exists(doc.id) and not force:
        console.print("  → [yellow]Already ingested.[/yellow] Use --force to re-ingest.")
        return db.get_document(doc.id)  # type: ignore[return-value]
    if force and db.document_exists(doc.id):
        console.print("  → [yellow]Force re-ingesting...[/yellow]")

    # 4. ATTACHMENTS — extract attachments to vault
    console.print("[dim]ATTACHMENTS[/dim] Extracting attachments...")
    attachments = plugin.extract_attachments(source, config.vault_attachments_dir)
    doc.attachments = attachments
    if attachments:
        console.print(f"  → {len(attachments)} attachment(s)")

    # 5. SUMMARIZE — LLM generates summary
    console.print("[dim]SUMMARIZE[/dim] Generating summary...")
    content_excerpt = doc.content[:4000]
    summary_prompt = SUMMARIZE_PROMPT.format(title=doc.title, content=content_excerpt)
    doc.summary = llm.complete(summary_prompt, max_tokens=512)
    console.print(f"  → Summary: {len(doc.summary)} chars")

    # 6. KEYWORDS — LLM extracts keywords
    console.print("[dim]KEYWORDS[/dim] Extracting keywords...")
    kw_prompt = KEYWORDS_PROMPT.format(title=doc.title, content=content_excerpt)
    kw_response = llm.complete(kw_prompt, max_tokens=128, temperature=0.2)
    doc.keywords = [k.strip().lower() for k in kw_response.split(",") if k.strip()][:10]
    console.print(f"  → Keywords: {', '.join(doc.keywords)}")

    # 7. CHUNK — split content into overlapping chunks
    console.print("[dim]CHUNK[/dim] Splitting into chunks...")
    chunks = chunk_text(doc.id, doc.content, config.chunk_size, config.chunk_overlap)
    console.print(f"  → {len(chunks)} chunks")

    # 8. EMBED — encode chunks and upsert to ChromaDB
    console.print("[dim]EMBED[/dim] Generating embeddings...")
    if chunks:
        embeddings = embed_texts(
            [c.content for c in chunks], model_name=config.embedding_model
        )
        vectorstore.upsert_chunks(chunks, embeddings)
    console.print(f"  → Stored {len(chunks)} vectors")

    # 9. LINK — find related documents via vector similarity + LLM
    console.print("[dim]LINK[/dim] Finding related documents...")
    doc.wikilinks = find_links(
        doc, db, vectorstore, llm, embedding_model=config.embedding_model
    )
    if doc.wikilinks:
        console.print(f"  → Linked to: {', '.join(doc.wikilinks)}")
    else:
        console.print("  → No related documents found (yet)")

    # 10. WRITE — save to SQLite + generate Obsidian page
    console.print("[dim]WRITE[/dim] Saving to database and vault...")
    doc.updated_at = utcnow()
    db.upsert_document(doc)

    # Store wikilinks in the database by resolving titles to IDs
    target_ids = []
    for title in doc.wikilinks:
        target = db.get_document_by_title(title)
        if target:
            target_ids.append(target.id)
    db.set_wikilinks(doc.id, target_ids)

    md_path = write_document(doc, config.vault_kb_dir)
    console.print(f"  → Vault page: [green]{md_path}[/green]")

    console.print(f"\n[bold green]Done![/bold green] Ingested: {doc.title}")
    return doc


def relink_document(
    doc: Document,
    config: Config,
    db: Database,
    vectorstore: VectorStore,
    llm: LLMProvider,
) -> Document:
    """Re-run linking for a single document and update its vault page."""
    doc.wikilinks = find_links(
        doc, db, vectorstore, llm, embedding_model=config.embedding_model
    )
    doc.updated_at = utcnow()
    db.upsert_document(doc)

    target_ids = []
    for title in doc.wikilinks:
        target = db.get_document_by_title(title)
        if target:
            target_ids.append(target.id)
    db.set_wikilinks(doc.id, target_ids)

    write_document(doc, config.vault_kb_dir)
    return doc
