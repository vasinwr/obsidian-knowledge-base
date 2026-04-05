"""ChromaDB wrapper for vector storage and semantic search."""

from __future__ import annotations

from pathlib import Path

from kb.models import Chunk


class VectorStore:
    """Persistent ChromaDB vector store."""

    COLLECTION_NAME = "kb_chunks"

    def __init__(self, persist_dir: Path) -> None:
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Upsert chunks with their embeddings into ChromaDB."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.content for c in chunks],
            metadatas=[
                {
                    "document_id": c.document_id,
                    "index": c.index,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                }
                for c in chunks
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        exclude_doc_id: str | None = None,
    ) -> list[dict]:
        """Search for similar chunks.

        Returns a list of dicts with keys: id, document_id, content, score, metadata.
        """
        # Fetch extra results if we need to filter out a document
        fetch_n = n_results + 20 if exclude_doc_id else n_results

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(fetch_n, self._collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        for i in range(len(results["ids"][0])):
            doc_id = results["metadatas"][0][i]["document_id"]
            if exclude_doc_id and doc_id == exclude_doc_id:
                continue
            hits.append(
                {
                    "id": results["ids"][0][i],
                    "document_id": doc_id,
                    "content": results["documents"][0][i],
                    "score": 1.0 - results["distances"][0][i],  # cosine distance → similarity
                    "metadata": results["metadatas"][0][i],
                }
            )
            if len(hits) >= n_results:
                break

        return hits

    def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a document."""
        self._collection.delete(where={"document_id": document_id})

    def count(self) -> int:
        """Return total number of stored chunks."""
        return self._collection.count()
