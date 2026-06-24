"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.services.sources.models import SourceChunk
from mvc.agent_gateway.indexing_gateway import IndexRepository
from mvc.models.document import Document


class KnowledgeSourceProvider:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - source_type（类属性或 ORM 字段）：保存source_type相关状态、配置或数据字段。
    - index_repository（实例属性，由构造函数注入或初始化）：保存index_repository相关状态、配置或数据字段。
    """
    source_type = "knowledge"

    def __init__(self, index_repository: IndexRepository | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - index_repository（IndexRepository | None）：调用方传入的index_repository数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.index_repository = index_repository or IndexRepository()

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_ids: list[str],
        max_chunks: int,
    ) -> list[SourceChunk]:
        """
        用途：异步执行collect相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str]）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - max_chunks（int）：调用方传入的max_chunks数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not source_ids:
            return []

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.source_type == "knowledge",
                Document.id.in_(source_ids),
            )
        )
        documents = {doc.id: doc for doc in result.scalars().all()}
        chunks: list[SourceChunk] = []
        for source_id in source_ids:
            document = documents.get(source_id)
            if not document:
                continue
            indexed_chunks = await self.index_repository.list_source_chunks(
                user_id=user_id,
                source_type="knowledge",
                source_id=source_id,
            )
            for chunk in indexed_chunks:
                chunks.append(
                    SourceChunk(
                        source_type="knowledge",
                        source_id=document.id,
                        title=document.title,
                        content=chunk.content,
                        chunk_id=chunk.id,
                    )
                )
                if len(chunks) >= max_chunks:
                    return chunks
        return chunks

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        """
        用途：异步执行search相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str] | None）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        chunks = await self.index_repository.search(
            user_id=user_id,
            query=query,
            source_type="knowledge",
            source_ids=source_ids,
            top_k=top_k,
        )
        doc_ids = {chunk.source_id for chunk in chunks}
        if not doc_ids:
            return []

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.source_type == "knowledge",
                Document.id.in_(doc_ids),
            )
        )
        documents = {doc.id: doc for doc in result.scalars().all()}
        return [
            SourceChunk(
                source_type="knowledge",
                source_id=chunk.source_id,
                title=documents.get(chunk.source_id).title if chunk.source_id in documents else str(chunk.metadata.get("original_filename") or "知识库文档"),
                content=chunk.content,
                chunk_id=chunk.id,
                score=chunk.score,
            )
            for chunk in chunks
        ]
