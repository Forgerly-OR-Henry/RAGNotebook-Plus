"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceChunk:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    - source_id（str）：保存source_id相关状态、配置或数据字段。
    - title（str）：保存title相关状态、配置或数据字段。
    - content（str）：保存content相关状态、配置或数据字段。
    - chunk_id（str | None）：保存chunk_id相关状态、配置或数据字段。
    - score（float | None）：保存score相关状态、配置或数据字段。
    """
    source_type: str
    source_id: str
    title: str
    content: str
    chunk_id: str | None = None
    score: float | None = None

    def citation(self) -> dict:
        """
        用途：执行citation相关业务逻辑。

        参数：无显式业务参数。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
        quote = self.content.strip().replace("\n", " ")
        if len(quote) > 220:
            quote = quote[:220] + "..."
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "chunk_id": self.chunk_id,
            "quote": quote,
            "score": self.score,
        }


def format_source_context(chunks: list[SourceChunk], max_chars: int = 8000) -> str:
    """
    用途：格式化format source context相关的数据或流程。

    参数：
    - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。
    - max_chars（int）：调用方传入的max_chars数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    parts = []
    total = 0
    for idx, chunk in enumerate(chunks, 1):
        item = f"[{idx}] 来源:{chunk.source_type} 标题:{chunk.title}\n{chunk.content.strip()}\n"
        if total + len(item) > max_chars:
            break
        parts.append(item)
        total += len(item)
    return "\n".join(parts)
