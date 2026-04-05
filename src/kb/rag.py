"""RAG Q&A engine with citations."""

from __future__ import annotations

import re

from kb.database import Database
from kb.embeddings import embed_text
from kb.llm import LLMProvider
from kb.models import Answer, Citation
from kb.vectorstore import VectorStore

RAG_PROMPT = """You are a knowledgeable assistant answering questions based on the provided sources.

## Sources
{sources}

## Question
{question}

## Instructions
Answer the question using ONLY the information from the provided sources. Cite your sources inline using [Source N] format (e.g., [Source 1], [Source 2]).
If the sources don't contain enough information to answer, say so clearly.
Be concise but thorough.

Answer:"""


def ask(
    question: str,
    db: Database,
    vectorstore: VectorStore,
    llm: LLMProvider,
    *,
    embedding_model: str = "all-MiniLM-L6-v2",
    n_results: int = 8,
) -> Answer:
    """Answer a question using RAG with citations.

    1. Embed the question.
    2. Retrieve top-N chunks from ChromaDB.
    3. Load parent documents for context.
    4. Construct prompt with sources.
    5. LLM generates answer with inline citations.
    6. Parse response and extract referenced citations.
    """
    query_vec = embed_text(question, model_name=embedding_model)
    hits = vectorstore.search(query_vec, n_results=n_results)

    if not hits:
        return Answer(text="No relevant documents found in the knowledge base.")

    # Build sources with parent document info
    sources: list[dict] = []
    seen_doc_ids: set[str] = set()
    for hit in hits:
        doc = db.get_document(hit["document_id"])
        if not doc:
            continue
        sources.append(
            {
                "index": len(sources) + 1,
                "title": doc.title,
                "source_url": doc.source_url,
                "chunk_text": hit["content"],
                "document_id": doc.id,
            }
        )
        seen_doc_ids.add(doc.id)

    if not sources:
        return Answer(text="No relevant documents found in the knowledge base.")

    # Format sources for the prompt
    source_text = "\n\n".join(
        f"[Source {s['index']}] (from \"{s['title']}\")\n{s['chunk_text']}"
        for s in sources
    )

    prompt = RAG_PROMPT.format(sources=source_text, question=question)
    response = llm.complete(prompt, max_tokens=2048, temperature=0.2)

    # Parse citations from response
    cited_indices = set(int(m) for m in re.findall(r"\[Source (\d+)\]", response))

    citations = []
    for s in sources:
        if s["index"] in cited_indices:
            citations.append(
                Citation(
                    document_title=s["title"],
                    source_url=s["source_url"],
                    chunk_text=s["chunk_text"],
                )
            )

    return Answer(text=response, citations=citations)
