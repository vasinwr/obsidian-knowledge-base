"""PDF source plugin using pymupdf4llm."""

from __future__ import annotations

import shutil
from pathlib import Path

from kb.models import Document, SourceType
from kb.plugins.base import SourcePlugin
from kb.utils import content_hash, utcnow


class PdfPlugin(SourcePlugin):
    @property
    def name(self) -> str:
        return "pdf"

    @property
    def source_type(self) -> SourceType:
        return SourceType.PDF

    def can_handle(self, source: str) -> bool:
        return source.lower().endswith(".pdf") or (
            source.startswith("http") and ".pdf" in source.lower()
        )

    def ingest(self, source: str) -> Document:
        local_path = self._resolve_path(source)

        import pymupdf4llm

        text = pymupdf4llm.to_markdown(str(local_path))
        if not text.strip():
            raise RuntimeError(f"No extractable text in PDF: {source}")

        title = local_path.stem.replace("-", " ").replace("_", " ").title()

        now = utcnow()
        return Document(
            id=content_hash(source),
            title=title,
            source_url=source,
            source_type=SourceType.PDF,
            content=text,
            created_at=now,
            updated_at=now,
        )

    def extract_attachments(self, source: str, dest_dir: Path) -> list[str]:
        local_path = self._resolve_path(source)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / local_path.name
        if not dest.exists():
            shutil.copy2(local_path, dest)
        return [local_path.name]

    def _resolve_path(self, source: str) -> Path:
        """Resolve to a local file path, downloading if necessary."""
        if source.startswith("http"):
            return self._download(source)
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {source}")
        return path

    @staticmethod
    def _download(url: str) -> Path:
        import tempfile

        import httpx

        resp = httpx.get(url, follow_redirects=True, timeout=60)
        resp.raise_for_status()
        suffix = ".pdf"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return Path(tmp.name)
