"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.services.sources import SourceChunk, SourceRegistry, format_source_context, get_source_registry


class SourceCollector:
    """Backward-compatible adapter over the domain source registry."""

    async def collect(self, db, user_id: str, source_type: str, source_ids: list[str], max_chunks: int = 12) -> list[SourceChunk]:
        """
        用途：异步执行collect相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str]）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - max_chunks（int）：调用方传入的max_chunks数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceChunk]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await get_source_registry().collect(db, user_id, source_type, source_ids, max_chunks=max_chunks)


__all__ = ["SourceChunk", "SourceCollector", "SourceRegistry", "format_source_context", "get_source_registry"]
