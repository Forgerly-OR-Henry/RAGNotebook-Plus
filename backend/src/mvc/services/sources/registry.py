"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from mvc.services.sources.interfaces import SourceProvider
from mvc.services.sources.models import SourceChunk


class SourceRegistry:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - providers（实例属性，由构造函数注入或初始化）：保存providers相关状态、配置或数据字段。
    """
    def __init__(self, providers: list[SourceProvider]):
        """
        用途：执行init相关业务逻辑。

        参数：
        - providers（list[SourceProvider]）：调用方传入的providers数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.providers = {provider.source_type: provider for provider in providers}

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_type: str,
        source_ids: list[str],
        max_chunks: int = 12,
    ) -> list[SourceChunk]:
        """
        用途：异步执行collect相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str]）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - max_chunks（int）：调用方传入的max_chunks数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        chunks: list[SourceChunk] = []
        normalized_ids = [sid for sid in source_ids if sid]
        for provider in self._providers_for(source_type):
            chunks.extend(await provider.collect(db, user_id, normalized_ids, max_chunks=max_chunks))
            if len(chunks) >= max_chunks:
                break
        return chunks[:max_chunks]

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        source_type: str = "mixed",
        top_k: int = 6,
        source_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        """
        用途：异步执行search相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str] | None）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        chunks: list[SourceChunk] = []
        for provider in self._providers_for(source_type):
            chunks.extend(await provider.search(db, user_id, query, top_k=top_k, source_ids=source_ids))
        chunks.sort(key=lambda chunk: chunk.score if chunk.score is not None else 999999.0)
        return chunks[:top_k]

    def _providers_for(self, source_type: str) -> list[SourceProvider]:
        """
        用途：执行providers for相关业务逻辑。

        参数：
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceProvider]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        if source_type == "mixed":
            return [self.providers[key] for key in ("note", "knowledge") if key in self.providers]
        provider = self.providers.get(source_type)
        return [provider] if provider else []


_source_registry: SourceRegistry | None = None


def get_source_registry() -> SourceRegistry:
    """
    用途：读取或查询get source registry相关的数据或流程。

    参数：无显式业务参数。

    返回：SourceRegistry；返回值供调用方继续编排业务流程或生成接口响应。
    """
    global _source_registry
    if _source_registry is None:
        from mvc.services.sources.knowledge_provider import KnowledgeSourceProvider
        from mvc.services.sources.note_provider import NoteSourceProvider

        _source_registry = SourceRegistry([NoteSourceProvider(), KnowledgeSourceProvider()])
    return _source_registry
