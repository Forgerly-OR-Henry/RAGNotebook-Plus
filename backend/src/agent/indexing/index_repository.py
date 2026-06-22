from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from langchain_core.documents import Document
from sqlalchemy import text

from core.background_init import init_manager
from core.logger_handler import logger
from db.db_config import AsyncSessionLocal


@dataclass
class IndexChunk:
    id: str
    source_type: str
    source_id: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    score: float | None = None


class IndexRepository:
    """Unified pgvector repository for all indexed sources."""

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model

    def _embedding_model(self):
        model = self.embedding_model or init_manager.embed_model
        if model is None:
            raise RuntimeError("Embedding model is not initialized")
        return model

    @staticmethod
    def chunk_id(source_type: str, source_id: str, chunk_index: int) -> str:
        digest = hashlib.sha1(f"{source_type}:{source_id}:{chunk_index}".encode("utf-8")).hexdigest()
        return digest[:40]

    @staticmethod
    def _vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(str(float(x)) for x in embedding) + "]"

    async def upsert_documents(
        self,
        *,
        source_type: str,
        source_id: str,
        user_id: str,
        documents: list[Document],
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        if not documents:
            return []

        model = self._embedding_model()
        contents = [doc.page_content for doc in documents]
        embeddings = await self._embed_documents(model, contents)
        now = datetime.now(timezone.utc)
        rows = []
        ids = []

        for index, (doc, embedding) in enumerate(zip(documents, embeddings)):
            chunk_metadata = dict(metadata or {})
            chunk_metadata.update(doc.metadata or {})
            chunk_metadata.update(
                {
                    "user_id": user_id,
                    "source_type": source_type,
                    "source_id": source_id,
                    "chunk_index": index,
                }
            )
            row_id = self.chunk_id(source_type, source_id, index)
            ids.append(row_id)
            rows.append(
                {
                    "id": row_id,
                    "source_type": source_type,
                    "document_id": source_id,
                    "user_id": user_id,
                    "chunk_index": index,
                    "content": doc.page_content,
                    "content_hash": hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest(),
                    "metadata": json.dumps(chunk_metadata, ensure_ascii=False),
                    "embedding": self._vector_literal(embedding),
                    "created_at": now,
                    "updated_at": now,
                }
            )

        stmt = text(
            """
            INSERT INTO index_chunks (id, document_id, user_id, source_type, chunk_index, content, content_hash, metadata, embedding, created_at, updated_at)
            VALUES (:id, :document_id, :user_id, :source_type, :chunk_index, :content, :content_hash, CAST(:metadata AS jsonb), CAST(:embedding AS vector), :created_at, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                source_type = EXCLUDED.source_type,
                user_id = EXCLUDED.user_id,
                chunk_index = EXCLUDED.chunk_index,
                content = EXCLUDED.content,
                content_hash = EXCLUDED.content_hash,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                updated_at = EXCLUDED.updated_at
            """
        )
        async with AsyncSessionLocal() as session:
            await session.execute(stmt, rows)
            await session.commit()
        return ids

    async def _embed_documents(self, model, contents: list[str]) -> list[list[float]]:
        try:
            return await self._to_thread(model.embed_documents, contents)
        except AttributeError:
            return [await self._to_thread(model.embed_query, content) for content in contents]

    async def _embed_query(self, query: str) -> list[float]:
        return await self._to_thread(self._embedding_model().embed_query, query)

    @staticmethod
    async def _to_thread(func, *args):
        import asyncio

        return await asyncio.to_thread(func, *args)

    async def search(
        self,
        *,
        user_id: str,
        query: str,
        source_type: str | None = None,
        source_ids: list[str] | None = None,
        top_k: int = 4,
    ) -> list[IndexChunk]:
        query_embedding = await self._embed_query(query)
        params: dict[str, Any] = {
            "user_id": user_id,
            "query_embedding": self._vector_literal(query_embedding),
            "limit": top_k,
        }
        clauses = ["user_id = :user_id"]
        if source_type:
            clauses.append("source_type = :source_type")
            params["source_type"] = source_type
        if source_ids:
            id_params = []
            for idx, source_id in enumerate(source_ids):
                key = f"sid_{idx}"
                id_params.append(f":{key}")
                params[key] = source_id
            clauses.append(f"document_id IN ({', '.join(id_params)})")

        stmt = text(
            f"""
            SELECT id, source_type, document_id, chunk_index, content, metadata,
                   embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM index_chunks
            WHERE {' AND '.join(clauses)}
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, params)
            rows = result.mappings().all()

        return [
            IndexChunk(
                id=row["id"],
                source_type=row["source_type"],
                source_id=row["document_id"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                metadata=dict(row["metadata"] or {}),
                score=float(row["distance"]) if row["distance"] is not None else None,
            )
            for row in rows
        ]

    async def list_source_chunks(self, *, user_id: str, source_type: str, source_id: str) -> list[IndexChunk]:
        stmt = text(
            """
            SELECT id, source_type, document_id, chunk_index, content, metadata
            FROM index_chunks
            WHERE user_id = :user_id AND source_type = :source_type AND document_id = :source_id
            ORDER BY chunk_index ASC
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                stmt,
                {"user_id": user_id, "source_type": source_type, "source_id": source_id},
            )
            rows = result.mappings().all()
        return [
            IndexChunk(
                id=row["id"],
                source_type=row["source_type"],
                source_id=row["document_id"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                metadata=dict(row["metadata"] or {}),
            )
            for row in rows
        ]

    async def delete_source(self, *, user_id: str, source_type: str, source_id: str) -> int:
        stmt = text(
            """
            DELETE FROM index_chunks
            WHERE user_id = :user_id AND source_type = :source_type AND document_id = :source_id
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id, "source_type": source_type, "source_id": source_id})
            await session.commit()
            return result.rowcount or 0

    async def delete_user_source_type(self, *, user_id: str, source_type: str) -> int:
        stmt = text("DELETE FROM index_chunks WHERE user_id = :user_id AND source_type = :source_type")
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id, "source_type": source_type})
            await session.commit()
            return result.rowcount or 0


def assert_embedding_dimension(embedding: list[float]) -> None:
    expected = embedding_dimension()
    actual = len(embedding or [])
    if actual != expected:
        logger.error("Embedding dimension mismatch: expected %s, got %s", expected, actual)
        raise RuntimeError(f"EMBEDDING_DIM={expected} 与当前嵌入模型实际维度 {actual} 不一致")


def embedding_dimension() -> int:
    return int(os.getenv("EMBEDDING_DIM", "1024"))
