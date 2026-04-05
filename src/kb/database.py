"""SQLite metadata store for documents, keywords, wikilinks, and attachments."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from kb.models import Document, ReadStatus, SourceType

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    read_status TEXT NOT NULL DEFAULT 'not_read',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS keywords (
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    PRIMARY KEY (document_id, keyword)
);

CREATE TABLE IF NOT EXISTS wikilinks (
    source_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, target_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    original_name TEXT NOT NULL
);
"""


class Database:
    """SQLite-backed metadata store."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ── Document CRUD ──────────────────────────────────────────────

    def upsert_document(self, doc: Document) -> None:
        """Insert or replace a document and its related rows."""
        self._conn.execute(
            """INSERT OR REPLACE INTO documents
               (id, title, source_url, source_type, content, summary,
                read_status, created_at, updated_at, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc.id,
                doc.title,
                doc.source_url,
                doc.source_type.value,
                doc.content,
                doc.summary,
                doc.read_status.value,
                doc.created_at.isoformat(),
                doc.updated_at.isoformat(),
                json.dumps(doc.metadata),
            ),
        )
        # Replace keywords
        self._conn.execute("DELETE FROM keywords WHERE document_id = ?", (doc.id,))
        for kw in doc.keywords:
            self._conn.execute(
                "INSERT INTO keywords (document_id, keyword) VALUES (?, ?)",
                (doc.id, kw),
            )
        # Replace attachments
        self._conn.execute("DELETE FROM attachments WHERE document_id = ?", (doc.id,))
        for att in doc.attachments:
            self._conn.execute(
                "INSERT INTO attachments (document_id, file_path, original_name) VALUES (?, ?, ?)",
                (doc.id, att, att.split("/")[-1] if "/" in att else att),
            )
        self._conn.commit()

    def get_document(self, doc_id: str) -> Document | None:
        """Fetch a document by ID (full or prefix)."""
        row = self._conn.execute(
            "SELECT * FROM documents WHERE id = ? OR id LIKE ?",
            (doc_id, f"{doc_id}%"),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    def get_document_by_title(self, title: str) -> Document | None:
        """Fetch a document by exact title."""
        row = self._conn.execute(
            "SELECT * FROM documents WHERE title = ?", (title,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    def find_document(self, id_or_title: str) -> Document | None:
        """Find by ID prefix or title."""
        doc = self.get_document(id_or_title)
        if doc:
            return doc
        return self.get_document_by_title(id_or_title)

    def list_documents(
        self,
        *,
        unread_only: bool = False,
        source_type: str | None = None,
    ) -> list[Document]:
        """List documents with optional filters."""
        query = "SELECT * FROM documents WHERE 1=1"
        params: list = []
        if unread_only:
            query += " AND read_status = ?"
            params.append("not_read")
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_document(r) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its related rows. Returns True if found."""
        cur = self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def document_exists(self, doc_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return row is not None

    def rename_document(self, doc_id: str, new_title: str) -> bool:
        """Update a document's title. Returns True if document found."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (new_title, now, doc_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def set_read_status(self, doc_id: str, status: ReadStatus) -> bool:
        """Update read status. Returns True if document found."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "UPDATE documents SET read_status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, doc_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    # ── Wikilinks ──────────────────────────────────────────────────

    def set_wikilinks(self, source_id: str, target_ids: list[str]) -> None:
        """Replace all outgoing wikilinks for a document."""
        self._conn.execute("DELETE FROM wikilinks WHERE source_id = ?", (source_id,))
        for tid in target_ids:
            self._conn.execute(
                "INSERT OR IGNORE INTO wikilinks (source_id, target_id) VALUES (?, ?)",
                (source_id, tid),
            )
        self._conn.commit()

    def get_wikilink_targets(self, source_id: str) -> list[str]:
        """Get IDs of documents this document links to."""
        rows = self._conn.execute(
            "SELECT target_id FROM wikilinks WHERE source_id = ?", (source_id,)
        ).fetchall()
        return [r[0] for r in rows]

    # ── Keywords ───────────────────────────────────────────────────

    def get_documents_by_keyword(self, keyword: str) -> list[str]:
        """Return document IDs that have this keyword."""
        rows = self._conn.execute(
            "SELECT document_id FROM keywords WHERE keyword = ?", (keyword,)
        ).fetchall()
        return [r[0] for r in rows]

    def get_all_keywords(self) -> list[str]:
        """Return all unique keywords."""
        rows = self._conn.execute(
            "SELECT DISTINCT keyword FROM keywords ORDER BY keyword"
        ).fetchall()
        return [r[0] for r in rows]

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return aggregate statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        unread = self._conn.execute(
            "SELECT COUNT(*) FROM documents WHERE read_status = 'not_read'"
        ).fetchone()[0]
        by_type = dict(
            self._conn.execute(
                "SELECT source_type, COUNT(*) FROM documents GROUP BY source_type"
            ).fetchall()
        )
        keywords = self._conn.execute("SELECT COUNT(DISTINCT keyword) FROM keywords").fetchone()[0]
        links = self._conn.execute("SELECT COUNT(*) FROM wikilinks").fetchone()[0]
        return {
            "total_documents": total,
            "unread": unread,
            "read": total - unread,
            "by_type": by_type,
            "unique_keywords": keywords,
            "wikilinks": links,
        }

    # ── Helpers ────────────────────────────────────────────────────

    def _row_to_document(self, row: tuple) -> Document:
        doc_id = row[0]
        keywords = [
            r[0]
            for r in self._conn.execute(
                "SELECT keyword FROM keywords WHERE document_id = ?", (doc_id,)
            ).fetchall()
        ]
        attachments = [
            r[0]
            for r in self._conn.execute(
                "SELECT file_path FROM attachments WHERE document_id = ?", (doc_id,)
            ).fetchall()
        ]
        target_ids = self.get_wikilink_targets(doc_id)
        wikilink_titles = []
        for tid in target_ids:
            title_row = self._conn.execute(
                "SELECT title FROM documents WHERE id = ?", (tid,)
            ).fetchone()
            if title_row:
                wikilink_titles.append(title_row[0])

        return Document(
            id=doc_id,
            title=row[1],
            source_url=row[2],
            source_type=SourceType(row[3]),
            content=row[4],
            summary=row[5],
            read_status=ReadStatus(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
            metadata=json.loads(row[9]),
            keywords=keywords,
            wikilinks=wikilink_titles,
            attachments=attachments,
        )
