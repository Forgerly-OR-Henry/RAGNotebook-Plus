"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from mvc.services.sources.models import SourceChunk


class SourceProvider(Protocol):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    """
    source_type: str

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
        ...

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
        ...
