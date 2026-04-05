"""LLM-powered wikilink generation between documents."""

from __future__ import annotations

from kb.database import Database
from kb.embeddings import embed_text
from kb.llm import LLMProvider
from kb.models import Document
from kb.vectorstore import VectorStore

LINK_PROMPT = """You are a knowledge-base assistant. Given a new document and a list of candidate documents, determine which candidates are genuinely related.

## New Document
Title: {title}
Summary: {summary}

## Candidate Documents
{candidates}

## Instructions
Return ONLY a JSON array of titles that are genuinely related to the new document. Maximum 10 titles. Return an empty array if none are related.
Only return titles from the candidate list above. Do not invent titles.

Example output: ["Title One", "Title Two"]

Related titles:"""


def find_links(
    doc: Document,
    db: Database,
    vectorstore: VectorStore,
    llm: LLMProvider,
    *,
    embedding_model: str = "all-MiniLM-L6-v2",
    max_candidates: int = 30,
    max_links: int = 10,
) -> list[str]:
    """Find related documents and return their titles as wikilink targets.

    1. Vector similarity search for top-20 similar chunks from other docs.
    2. Keyword overlap search from SQLite.
    3. Merge + deduplicate candidates.
    4. LLM judges which candidates are genuinely related.
    """
    candidate_ids: dict[str, str] = {}  # doc_id → title

    # Vector candidates
    summary_text = doc.summary or doc.content[:500]
    query_vec = embed_text(summary_text, model_name=embedding_model)
    hits = vectorstore.search(query_vec, n_results=20, exclude_doc_id=doc.id)
    for hit in hits:
        did = hit["document_id"]
        if did not in candidate_ids and did != doc.id:
            other = db.get_document(did)
            if other:
                candidate_ids[did] = other.title

    # Keyword candidates
    for kw in doc.keywords:
        for did in db.get_documents_by_keyword(kw):
            if did != doc.id and did not in candidate_ids:
                other = db.get_document(did)
                if other:
                    candidate_ids[did] = other.title

    if not candidate_ids:
        return []

    # Cap candidates
    candidates = list(candidate_ids.items())[:max_candidates]

    # Build candidate list for LLM
    candidate_text = "\n".join(
        f"- {title}" for _, title in candidates
    )

    prompt = LINK_PROMPT.format(
        title=doc.title,
        summary=doc.summary or doc.content[:300],
        candidates=candidate_text,
    )

    response = llm.complete(prompt, max_tokens=512, temperature=0.1)

    # Parse JSON array from response
    titles = _parse_title_list(response, {title for _, title in candidates})
    return titles[:max_links]


def _parse_title_list(response: str, valid_titles: set[str]) -> list[str]:
    """Extract a list of titles from the LLM response, filtering to valid ones."""
    import json

    # Try to parse as JSON array
    response = response.strip()
    # Find the JSON array in the response
    start = response.find("[")
    end = response.rfind("]")
    if start != -1 and end != -1:
        try:
            titles = json.loads(response[start : end + 1])
            if isinstance(titles, list):
                return [t for t in titles if isinstance(t, str) and t in valid_titles]
        except json.JSONDecodeError:
            pass

    # Fallback: line-by-line matching
    result = []
    for title in valid_titles:
        if title in response:
            result.append(title)
    return result
