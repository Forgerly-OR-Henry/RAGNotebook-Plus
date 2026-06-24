"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from langchain_core.documents import Document
from sqlalchemy import text

from core.background_init import init_manager
from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from utils.env_loader import require_env_int_value

_QUERY_EMBEDDING_CACHE: OrderedDict[tuple[int, str], list[float]] = OrderedDict()


def clear_query_embedding_cache() -> None:
    """
    用途：执行clear query embedding cache相关业务逻辑。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _QUERY_EMBEDDING_CACHE.clear()


@dataclass
class IndexChunk:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    - source_id（str）：保存source_id相关状态、配置或数据字段。
    - chunk_index（int）：保存chunk_index相关状态、配置或数据字段。
    - content（str）：保存content相关状态、配置或数据字段。
    - metadata（dict[str, Any]）：保存metadata相关状态、配置或数据字段。
    - score（float | None）：保存score相关状态、配置或数据字段。
    """
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
        """
        用途：执行init相关业务逻辑。

        参数：
        - embedding_model（未显式标注）：调用方传入的embedding_model数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.embedding_model = embedding_model

    def _embedding_model(self):
        """
        用途：执行embedding model相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        model = self.embedding_model or init_manager.embed_model
        if model is None:
            raise RuntimeError("Embedding model is not initialized")
        return model

    @staticmethod
    def chunk_id(source_type: str, source_id: str, chunk_index: int) -> str:
        """
        用途：执行chunk id相关业务逻辑。

        参数：
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。
        - chunk_index（int）：调用方传入的chunk_index数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        digest = hashlib.sha1(f"{source_type}:{source_id}:{chunk_index}".encode("utf-8")).hexdigest()
        return digest[:40]

    @staticmethod
    def _vector_literal(embedding: list[float]) -> str:
        """
        用途：执行vector literal相关业务逻辑。

        参数：
        - embedding（list[float]）：调用方传入的embedding数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
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
        """
        用途：异步执行upsert documents相关业务流程。

        参数：
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - documents（list[Document]）：调用方传入的documents数据或控制参数，用于驱动本函数处理流程。
        - metadata（dict[str, Any] | None）：调用方传入的metadata数据或控制参数，用于驱动本函数处理流程。

        返回：list[str]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行embed documents相关业务流程。

        参数：
        - model（未显式标注）：调用方传入的model数据或控制参数，用于驱动本函数处理流程。
        - contents（list[str]）：调用方传入的contents数据或控制参数，用于驱动本函数处理流程。

        返回：list[list[float]]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        try:
            return await self._to_thread(model.embed_documents, contents)
        except AttributeError:
            return [await self._to_thread(model.embed_query, content) for content in contents]

    async def _embed_query(self, query: str) -> list[float]:
        """
        用途：异步执行embed query相关业务流程。

        参数：
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。

        返回：list[float]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        model = self._embedding_model()
        cache_key = (id(model), query)
        cached = _QUERY_EMBEDDING_CACHE.get(cache_key)
        if cached is not None:
            _QUERY_EMBEDDING_CACHE.move_to_end(cache_key)
            return list(cached)

        embedding = await self._to_thread(model.embed_query, query)
        _QUERY_EMBEDDING_CACHE[cache_key] = list(embedding)
        max_size = max(1, require_env_int_value("QUERY_EMBEDDING_CACHE_MAX", 128))
        while len(_QUERY_EMBEDDING_CACHE) > max_size:
            _QUERY_EMBEDDING_CACHE.popitem(last=False)
        return embedding

    @staticmethod
    async def _to_thread(func, *args):
        """
        用途：异步执行to thread相关业务流程。

        参数：
        - func（未显式标注）：调用方传入的func数据或控制参数，用于驱动本函数处理流程。
        - args（未显式标注）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行search相关业务流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - source_type（str | None）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str] | None）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。

        返回：list[IndexChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：列出list source chunks相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。

        返回：list[IndexChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：删除delete source相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：删除delete user source type相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        stmt = text("DELETE FROM index_chunks WHERE user_id = :user_id AND source_type = :source_type")
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"user_id": user_id, "source_type": source_type})
            await session.commit()
            return result.rowcount or 0


def assert_embedding_dimension(embedding: list[float]) -> None:
    """
    用途：执行assert embedding dimension相关业务逻辑。

    参数：
    - embedding（list[float]）：调用方传入的embedding数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    expected = embedding_dimension()
    actual = len(embedding or [])
    if actual != expected:
        logger.error("Embedding dimension mismatch: expected %s, got %s", expected, actual)
        raise RuntimeError(f"EMBEDDING_DIM={expected} 与当前嵌入模型实际维度 {actual} 不一致")


def embedding_dimension() -> int:
    """
    用途：执行embedding dimension相关业务逻辑。

    参数：无显式业务参数。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    expected = require_env_int_value("EMBEDDING_DIM", 1024)
    if expected <= 0:
        raise RuntimeError(f"EMBEDDING_DIM 必须是正整数，当前值：{expected}")
    return expected
