"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from pydantic import BaseModel, Field

from mvc.schemas.sources import SourceCitation, SourceRefType


class MindMapGenerateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - source_type（SourceRefType）：保存source_type相关状态、配置或数据字段。
    - source_ids（list[str]）：保存source_ids相关状态、配置或数据字段。
    - max_nodes（int）：保存max_nodes相关状态、配置或数据字段。
    - max_depth（int）：保存max_depth相关状态、配置或数据字段。
    - focus（str | None）：保存focus相关状态、配置或数据字段。
    """
    source_type: SourceRefType
    source_ids: list[str] = Field(min_length=1, max_length=20)
    max_nodes: int = 40
    max_depth: int = 4
    focus: str | None = None


class MindMapNode(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - label（str）：保存label相关状态、配置或数据字段。
    - level（int）：保存level相关状态、配置或数据字段。
    - type（str）：保存type相关状态、配置或数据字段。
    - summary（str | None）：保存summary相关状态、配置或数据字段。
    - source_refs（list[str]）：保存source_refs相关状态、配置或数据字段。
    """
    id: str
    label: str
    level: int = 0
    type: str = "concept"
    summary: str | None = None
    source_refs: list[str] = []


class MindMapEdge(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - source（str）：保存source相关状态、配置或数据字段。
    - target（str）：保存target相关状态、配置或数据字段。
    - label（str | None）：保存label相关状态、配置或数据字段。
    """
    id: str
    source: str
    target: str
    label: str | None = None


class MindMapResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - mindmap_id（str）：保存mindmap_id相关状态、配置或数据字段。
    - title（str）：保存title相关状态、配置或数据字段。
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    - source_ids（list[str]）：保存source_ids相关状态、配置或数据字段。
    - nodes（list[MindMapNode]）：保存nodes相关状态、配置或数据字段。
    - edges（list[MindMapEdge]）：保存edges相关状态、配置或数据字段。
    - citations（list[SourceCitation]）：保存citations相关状态、配置或数据字段。
    - source_refs（list[dict]）：保存source_refs相关状态、配置或数据字段。
    - version（int）：保存version相关状态、配置或数据字段。
    """
    mindmap_id: str
    title: str
    source_type: str
    source_ids: list[str]
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
    citations: list[SourceCitation] = []
    source_refs: list[dict] = []
    version: int = 1


class MindMapUpdateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - title（str）：保存title相关状态、配置或数据字段。
    - nodes（list[MindMapNode]）：保存nodes相关状态、配置或数据字段。
    - edges（list[MindMapEdge]）：保存edges相关状态、配置或数据字段。
    """
    title: str
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
