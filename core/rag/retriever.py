"""Similarity search over ingested knowledge chunks."""

from __future__ import annotations

from typing import Optional

from core.rag.ingest import embed_text
from core.rag.store import get_chroma_fallback, get_vector_store


async def retrieve_context(
    query: str,
    workshop_id: str,
    doc_types: Optional[list[str]] = None,
    top_k: int = 5,
) -> str:
    """Return concatenated RAG context for orchestrator enrichment."""
    embedding = await embed_text(query)
    store = get_vector_store()
    try:
        chunks = await store.search(embedding, workshop_id, doc_types, top_k)
    except Exception:
        chunks = await get_chroma_fallback().search(embedding, workshop_id, doc_types, top_k)

    if not chunks:
        return ""

    parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        dtype = meta.get("doc_type", "unknown") if isinstance(meta, dict) else "unknown"
        parts.append(f"[{i}] ({dtype}) {chunk['content']}")
    return "\n\n".join(parts)
