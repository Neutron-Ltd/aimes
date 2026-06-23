"""
Vector store backends for RAG — pgvector (primary) with file-store fallback.
"""

from __future__ import annotations

import json
import math
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 1536


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self,
        content: str,
        embedding: list[float],
        doc_type: str,
        metadata: dict[str, Any],
    ) -> str:
        ...

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        doc_types: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        ...


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


class FileVectorStore(VectorStore):
    """JSON file-backed store when Chroma/pgvector are unavailable."""

    def __init__(self, path: Optional[str] = None) -> None:
        settings = get_settings()
        self._path = Path(path or settings.chroma_persist_dir) / "vectors.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(records), encoding="utf-8")

    async def upsert(
        self,
        content: str,
        embedding: list[float],
        doc_type: str,
        metadata: dict[str, Any],
    ) -> str:
        chunk_id = str(uuid.uuid4())
        records = self._load()
        records.append(
            {
                "id": chunk_id,
                "content": content,
                "embedding": embedding,
                "doc_type": doc_type,
                "metadata": metadata,
            }
        )
        self._save(records)
        return chunk_id

    async def search(
        self,
        embedding: list[float],
        doc_types: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        records = self._load()
        scored: list[tuple[float, dict[str, Any]]] = []
        for rec in records:
            if doc_types and rec.get("doc_type") not in doc_types:
                continue
            sim = _cosine_similarity(embedding, rec.get("embedding", []))
            scored.append((sim, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "content": r["content"],
                "metadata": {**r.get("metadata", {}), "doc_type": r.get("doc_type")},
                "distance": 1.0 - score,
            }
            for score, r in scored[:top_k]
        ]


class ChromaVectorStore(VectorStore):
    def __init__(self) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb not installed") from exc

        settings = get_settings()
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="mes_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(
        self,
        content: str,
        embedding: list[float],
        doc_type: str,
        metadata: dict[str, Any],
    ) -> str:
        chunk_id = str(uuid.uuid4())
        meta = {**metadata, "doc_type": doc_type}
        self._collection.upsert(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{k: str(v) for k, v in meta.items()}],
        )
        return chunk_id

    async def search(
        self,
        embedding: list[float],
        doc_types: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        where: Optional[dict[str, Any]] = None
        if doc_types:
            where = {"doc_type": {"$in": doc_types}}

        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        chunks: list[dict[str, Any]] = []
        if not results.get("documents"):
            return chunks
        for i, doc in enumerate(results["documents"][0]):
            chunks.append(
                {
                    "content": doc,
                    "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                    "distance": results.get("distances", [[]])[0][i] if results.get("distances") else None,
                }
            )
        return chunks


class PgVectorStore(VectorStore):
    """Uses n2admin.ai_knowledge_chunks when pgvector extension is available."""

    def __init__(self) -> None:
        self._available: Optional[bool] = None

    async def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            from sqlalchemy import text

            from core.db import get_session

            session = await get_session()
            try:
                await session.execute(text("SELECT 1 FROM n2admin.ai_knowledge_chunks LIMIT 1"))
            finally:
                await session.close()
            self._available = True
        except Exception as exc:
            logger.warning("pgvector store unavailable, will use Chroma: %s", exc)
            self._available = False
        return self._available

    async def upsert(
        self,
        content: str,
        embedding: list[float],
        doc_type: str,
        metadata: dict[str, Any],
    ) -> str:
        from sqlalchemy import text

        from core.db import get_session

        if not await self._check_available():
            raise RuntimeError("pgvector backend not available")

        chunk_id = str(uuid.uuid4())
        emb_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        session = await get_session()
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO n2admin.ai_knowledge_chunks
                        (id, doc_type, content, metadata, embedding, data_auth)
                    VALUES
                        (:id, :doc_type, :content, CAST(:metadata AS jsonb),
                         CAST(:embedding AS vector), :data_auth)
                    """
                ),
                {
                    "id": chunk_id,
                    "doc_type": doc_type,
                    "content": content,
                    "metadata": json.dumps(metadata),
                    "embedding": emb_literal,
                    "data_auth": "",
                },
            )
            await session.commit()
        finally:
            await session.close()
        return chunk_id

    async def search(
        self,
        embedding: list[float],
        doc_types: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import text

        from core.db import get_session

        if not await self._check_available():
            return []

        emb_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        type_filter = ""
        params: dict[str, Any] = {
            "embedding": emb_literal,
            "top_k": top_k,
        }
        if doc_types:
            type_filter = "WHERE doc_type = ANY(:doc_types)"
            params["doc_types"] = doc_types

        sql = f"""
            SELECT content, metadata,
                   embedding <=> CAST(:embedding AS vector) AS distance
            FROM n2admin.ai_knowledge_chunks
            {type_filter}
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """
        session = await get_session()
        try:
            result = await session.execute(text(sql), params)
            rows = result.mappings().all()
        finally:
            await session.close()
        return [
            {"content": r["content"], "metadata": r["metadata"], "distance": float(r["distance"])}
            for r in rows
        ]


_store: Optional[VectorStore] = None
_file_fallback: Optional[FileVectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is not None:
        return _store

    settings = get_settings()
    backend = settings.rag_backend.lower()
    if backend == "pgvector":
        _store = PgVectorStore()
    elif backend == "chroma":
        try:
            _store = ChromaVectorStore()
        except RuntimeError:
            logger.warning("Chroma unavailable — using file vector store")
            _store = FileVectorStore()
    else:
        _store = FileVectorStore()
    return _store


def get_chroma_fallback() -> FileVectorStore:
    global _file_fallback
    if _file_fallback is None:
        _file_fallback = FileVectorStore()
    return _file_fallback
