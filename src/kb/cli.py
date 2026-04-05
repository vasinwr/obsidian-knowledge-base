"""Typer CLI — all kb commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from kb.config import Config, ensure_dirs, load_config, save_config
from kb.database import Database
from kb.llm import LLMProvider
from kb.models import ReadStatus
from kb.vectorstore import VectorStore

app = typer.Typer(
    name="kb",
    help="Personal knowledge base with LLM-powered ingestion, semantic search, and Obsidian output.",
    no_args_is_help=True,
)
console = Console()


def _get_config() -> Config:
    return load_config()


def _get_db(config: Config) -> Database:
    return Database(config.sqlite_path)


def _get_vectorstore(config: Config) -> VectorStore:
    return VectorStore(config.chroma_dir)


def _get_llm(config: Config) -> LLMProvider:
    return LLMProvider.create(config)


# ── Init ───────────────────────────────────────────────────────────

@app.command()
def init(
    vault_path: Annotated[str, typer.Argument(help="Path to your Obsidian vault")],
) -> None:
    """First-time setup — creates config and required directories."""
    vault = Path(vault_path).expanduser().resolve()
    if not vault.exists():
        console.print(f"[red]Vault path does not exist:[/red] {vault}")
        raise typer.Exit(1)

    cfg = Config(vault_path=str(vault))
    save_config(cfg)
    ensure_dirs(cfg)
    console.print(f"[green]Initialized![/green] Config saved. Vault: {vault}")
    console.print(f"  Knowledge Base folder: {cfg.vault_kb_dir}")


# ── Ingest ─────────────────────────────────────────────────────────

@app.command()
def ingest(
    sources: Annotated[list[str], typer.Argument(help="URLs or file paths to ingest")],
    force: Annotated[bool, typer.Option("-f", "--force", help="Force re-ingest")] = False,
) -> None:
    """Ingest one or more documents into the knowledge base."""
    from kb.pipeline import ingest as run_ingest
    from kb.plugins import load_builtin_plugins, load_external_plugins

    cfg = _get_config()
    ensure_dirs(cfg)
    load_builtin_plugins()
    load_external_plugins(cfg.external_plugins_dir)

    db = _get_db(cfg)
    vs = _get_vectorstore(cfg)
    llm = _get_llm(cfg)

    try:
        for source in sources:
            try:
                run_ingest(source, cfg, db, vs, llm, force=force)
            except Exception as e:
                console.print(f"[red]Error ingesting {source}:[/red] {e}")
    finally:
        db.close()


# ── Search ─────────────────────────────────────────────────────────

@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("-n", "--limit", help="Max results")] = 10,
) -> None:
    """Semantic search across the knowledge base."""
    from kb.embeddings import embed_text

    cfg = _get_config()
    db = _get_db(cfg)
    vs = _get_vectorstore(cfg)

    try:
        query_vec = embed_text(query, model_name=cfg.embedding_model)
        hits = vs.search(query_vec, n_results=limit)

        if not hits:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title="Search Results")
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold")
        table.add_column("Score", width=6)
        table.add_column("Excerpt", max_width=60)

        seen: set[str] = set()
        rank = 0
        for hit in hits:
            doc = db.get_document(hit["document_id"])
            if not doc or doc.id in seen:
                continue
            seen.add(doc.id)
            rank += 1
            excerpt = hit["content"][:100].replace("\n", " ") + "..."
            table.add_row(str(rank), doc.title, f"{hit['score']:.2f}", excerpt)

        console.print(table)
    finally:
        db.close()


# ── Ask (RAG Q&A) ─────────────────────────────────────────────────

@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Question to ask")],
) -> None:
    """Ask a question — RAG-powered Q&A with citations."""
    from kb.rag import ask as rag_ask

    cfg = _get_config()
    db = _get_db(cfg)
    vs = _get_vectorstore(cfg)
    llm = _get_llm(cfg)

    try:
        answer = rag_ask(question, db, vs, llm, embedding_model=cfg.embedding_model)
        console.print()
        console.print(answer.text)
        if answer.citations:
            console.print("\n[bold]Sources:[/bold]")
            for i, c in enumerate(answer.citations, 1):
                console.print(f"  [{i}] {c.document_title} — {c.source_url}")
    finally:
        db.close()


# ── List ───────────────────────────────────────────────────────────

@app.command(name="list")
def list_docs(
    unread: Annotated[bool, typer.Option("--unread", help="Show only unread")] = False,
    source_type: Annotated[Optional[str], typer.Option("--type", help="Filter by source type")] = None,
) -> None:
    """List documents in the knowledge base."""
    cfg = _get_config()
    db = _get_db(cfg)

    try:
        docs = db.list_documents(unread_only=unread, source_type=source_type)
        if not docs:
            console.print("[yellow]No documents found.[/yellow]")
            return

        table = Table(title=f"Documents ({len(docs)})")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Title", style="bold")
        table.add_column("Type", width=10)
        table.add_column("Status", width=10)
        table.add_column("Created", width=12)

        for doc in docs:
            status_style = "green" if doc.read_status == ReadStatus.READ else "yellow"
            table.add_row(
                doc.id[:8],
                doc.title,
                doc.source_type.value,
                f"[{status_style}]{doc.read_status.value}[/{status_style}]",
                doc.created_at.strftime("%Y-%m-%d"),
            )
        console.print(table)
    finally:
        db.close()


# ── Show ───────────────────────────────────────────────────────────

@app.command()
def show(
    id_or_title: Annotated[str, typer.Argument(help="Document ID (prefix) or title")],
) -> None:
    """Show details of a specific document."""
    cfg = _get_config()
    db = _get_db(cfg)

    try:
        doc = db.find_document(id_or_title)
        if not doc:
            console.print(f"[red]Document not found:[/red] {id_or_title}")
            raise typer.Exit(1)

        console.print(f"[bold]{doc.title}[/bold]")
        console.print(f"  ID:      {doc.id[:8]}")
        console.print(f"  Source:  {doc.source_url}")
        console.print(f"  Type:    {doc.source_type.value}")
        console.print(f"  Status:  {doc.read_status.value}")
        console.print(f"  Created: {doc.created_at.strftime('%Y-%m-%d %H:%M')}")
        if doc.keywords:
            console.print(f"  Tags:    {', '.join(doc.keywords)}")
        if doc.wikilinks:
            console.print(f"  Links:   {', '.join(doc.wikilinks)}")
        if doc.summary:
            console.print(f"\n[dim]Summary:[/dim]\n{doc.summary}")
    finally:
        db.close()


# ── Read / Unread ──────────────────────────────────────────────────

@app.command()
def read(
    id_or_title: Annotated[str, typer.Argument(help="Document ID (prefix) or title")],
) -> None:
    """Mark a document as READ."""
    _set_status(id_or_title, ReadStatus.READ)


@app.command()
def unread(
    id_or_title: Annotated[str, typer.Argument(help="Document ID (prefix) or title")],
) -> None:
    """Mark a document as NOT_READ."""
    _set_status(id_or_title, ReadStatus.NOT_READ)


def _set_status(id_or_title: str, status: ReadStatus) -> None:
    from kb.obsidian import write_document

    cfg = _get_config()
    db = _get_db(cfg)

    try:
        doc = db.find_document(id_or_title)
        if not doc:
            console.print(f"[red]Document not found:[/red] {id_or_title}")
            raise typer.Exit(1)

        db.set_read_status(doc.id, status)
        doc.read_status = status
        write_document(doc, cfg.vault_kb_dir)
        console.print(f"[green]Marked as {status.value}:[/green] {doc.title}")
    finally:
        db.close()


# ── Delete ─────────────────────────────────────────────────────────

@app.command()
def delete(
    id_or_title: Annotated[str, typer.Argument(help="Document ID (prefix) or title")],
) -> None:
    """Delete a document from the knowledge base and vault."""
    from kb.obsidian import delete_document

    cfg = _get_config()
    db = _get_db(cfg)
    vs = _get_vectorstore(cfg)

    try:
        doc = db.find_document(id_or_title)
        if not doc:
            console.print(f"[red]Document not found:[/red] {id_or_title}")
            raise typer.Exit(1)

        db.delete_document(doc.id)
        vs.delete_by_document(doc.id)
        delete_document(doc, cfg.vault_kb_dir)
        console.print(f"[green]Deleted:[/green] {doc.title}")
    finally:
        db.close()


# ── Relink ─────────────────────────────────────────────────────────

@app.command()
def relink(
    id_or_title: Annotated[Optional[str], typer.Argument(help="Document ID or title (omit for all)")] = None,
) -> None:
    """Re-run LLM-powered linking for one or all documents."""
    from kb.pipeline import relink_document

    cfg = _get_config()
    db = _get_db(cfg)
    vs = _get_vectorstore(cfg)
    llm = _get_llm(cfg)

    try:
        if id_or_title:
            doc = db.find_document(id_or_title)
            if not doc:
                console.print(f"[red]Document not found:[/red] {id_or_title}")
                raise typer.Exit(1)
            relink_document(doc, cfg, db, vs, llm)
            console.print(f"[green]Relinked:[/green] {doc.title}")
        else:
            docs = db.list_documents()
            for doc in docs:
                console.print(f"Relinking: {doc.title}...")
                relink_document(doc, cfg, db, vs, llm)
            console.print(f"[green]Relinked {len(docs)} documents.[/green]")
    finally:
        db.close()


# ── Stats ──────────────────────────────────────────────────────────

@app.command()
def stats() -> None:
    """Show knowledge base statistics."""
    cfg = _get_config()
    db = _get_db(cfg)

    try:
        s = db.stats()
        console.print("[bold]Knowledge Base Stats[/bold]")
        console.print(f"  Total documents: {s['total_documents']}")
        console.print(f"  Read:            {s['read']}")
        console.print(f"  Unread:          {s['unread']}")
        console.print(f"  Unique keywords: {s['unique_keywords']}")
        console.print(f"  Wikilinks:       {s['wikilinks']}")
        if s["by_type"]:
            console.print("  By type:")
            for t, count in s["by_type"].items():
                console.print(f"    {t}: {count}")
    finally:
        db.close()


# ── Plugins ────────────────────────────────────────────────────────

@app.command()
def plugins() -> None:
    """List installed plugins."""
    from kb.plugins import list_plugins, load_builtin_plugins, load_external_plugins

    cfg = _get_config()
    load_builtin_plugins()
    load_external_plugins(cfg.external_plugins_dir)

    table = Table(title="Installed Plugins")
    table.add_column("Name", style="bold")
    table.add_column("Type")

    for p in list_plugins():
        table.add_row(p.name, p.source_type.value)
    console.print(table)
