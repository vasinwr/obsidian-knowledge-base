"""Sentence-transformers wrapper for generating text embeddings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_model_cache: dict[str, SentenceTransformer] = {}


def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Return a cached SentenceTransformer model instance."""
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer

        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def embed_texts(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    """Encode a list of texts into embedding vectors.

    Returns a list of float lists, one per input text.
    """
    model = get_model(model_name)
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [vec.tolist() for vec in embeddings]


def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Encode a single text into an embedding vector."""
    return embed_texts([text], model_name)[0]
