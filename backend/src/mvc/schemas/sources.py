"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from typing import Literal

from pydantic import BaseModel


SourceType = Literal["note", "knowledge", "mixed"]
SourceRefType = Literal["note", "knowledge"]
Difficulty = Literal["easy", "normal", "hard"]


class SourceReference(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - source_type（SourceRefType）：保存source_type相关状态、配置或数据字段。
    - source_id（str）：保存source_id相关状态、配置或数据字段。
    """
    source_type: SourceRefType
    source_id: str


class SourceCitation(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    - source_id（str）：保存source_id相关状态、配置或数据字段。
    - title（str）：保存title相关状态、配置或数据字段。
    - chunk_id（str | None）：保存chunk_id相关状态、配置或数据字段。
    - quote（str）：保存quote相关状态、配置或数据字段。
    - score（float | None）：保存score相关状态、配置或数据字段。
    """
    source_type: str
    source_id: str
    title: str
    chunk_id: str | None = None
    quote: str
    score: float | None = None
