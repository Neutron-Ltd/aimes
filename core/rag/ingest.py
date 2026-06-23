"""Document chunking and embedding for RAG ingestion."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import dashscope
from http import HTTPStatus

from core.config import get_settings
from core.logging import get_logger
from core.rag.store import EMBEDDING_DIM, get_chroma_fallback, get_vector_store

logger = get_logger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Deterministic fallback embedding when DashScope is unavailable."""
    digest = hashlib.sha256(text.encode()).digest()
    values: list[float] = []
    for i in range(dim):
        byte = digest[i % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    return values


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    if not settings.dashscope_api_key:
        return _hash_embedding(text)

    def _call() -> list[float]:
        response = dashscope.TextEmbedding.call(
            model=settings.rag_embedding_model,
            input=text,
            api_key=settings.dashscope_api_key,
        )
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(getattr(response, "message", "Embedding API error"))
        output = response.output
        embeddings = output.get("embeddings") if isinstance(output, dict) else getattr(output, "embeddings", None)
        if not embeddings:
            raise RuntimeError("Empty embedding response")
        vec = embeddings[0].get("embedding") if isinstance(embeddings[0], dict) else embeddings[0]["embedding"]
        return list(vec)

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:
        logger.warning("DashScope embedding failed, using hash fallback: %s", exc)
        return _hash_embedding(text)


async def ingest_document(
    doc_type: str,
    text: str,
    metadata: dict[str, Any],
    workshop_id: str,
) -> tuple[bool, str, str]:
    """
    Chunk, embed, and upsert a document. Returns (success, chunk_id, backend).
  Falls back to Chroma if pgvector upsert fails.
    """
    store = get_vector_store()
    chunks = _chunk_text(text)
    last_id = ""
    backend = get_settings().rag_backend

    for i, chunk in enumerate(chunks):
        embedding = await embed_text(chunk)
        chunk_meta = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
        try:
            last_id = await store.upsert(chunk, embedding, doc_type, chunk_meta, workshop_id)
        except Exception as exc:
            logger.warning("Primary RAG store failed, falling back to Chroma: %s", exc)
            chroma = get_chroma_fallback()
            last_id = await chroma.upsert(chunk, embedding, doc_type, chunk_meta, workshop_id)
            backend = "file"

    return True, last_id, backend
