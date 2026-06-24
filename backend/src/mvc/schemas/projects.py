"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from pydantic import BaseModel, Field

from mvc.schemas.sources import SourceReference, SourceRefType


class ProjectCreateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - name（str）：保存name相关状态、配置或数据字段。
    - description（str | None）：保存description相关状态、配置或数据字段。
    """
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None


class ProjectUpdateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - name（str | None）：保存name相关状态、配置或数据字段。
    - description（str | None）：保存description相关状态、配置或数据字段。
    """
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None


class ProjectResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - user_id（str）：保存user_id相关状态、配置或数据字段。
    - name（str）：保存name相关状态、配置或数据字段。
    - description（str | None）：保存description相关状态、配置或数据字段。
    - source_count（int）：保存source_count相关状态、配置或数据字段。
    - session_count（int）：保存session_count相关状态、配置或数据字段。
    - created_at（str | None）：保存created_at相关状态、配置或数据字段。
    - updated_at（str | None）：保存updated_at相关状态、配置或数据字段。
    """
    id: str
    user_id: str
    name: str
    description: str | None = None
    source_count: int = 0
    session_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class ProjectListResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - projects（list[ProjectResponse]）：保存projects相关状态、配置或数据字段。
    - total_count（int）：保存total_count相关状态、配置或数据字段。
    """
    projects: list[ProjectResponse]
    total_count: int


class ProjectSourceResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - project_id（str）：保存project_id相关状态、配置或数据字段。
    - source_type（SourceRefType）：保存source_type相关状态、配置或数据字段。
    - source_id（str）：保存source_id相关状态、配置或数据字段。
    - title（str）：保存title相关状态、配置或数据字段。
    - preview（str | None）：保存preview相关状态、配置或数据字段。
    - status（str | None）：保存status相关状态、配置或数据字段。
    - created_at（str | None）：保存created_at相关状态、配置或数据字段。
    """
    id: str
    project_id: str
    source_type: SourceRefType
    source_id: str
    title: str
    preview: str | None = None
    status: str | None = None
    created_at: str | None = None


class ProjectSourcesResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - sources（list[ProjectSourceResponse]）：保存sources相关状态、配置或数据字段。
    - total_count（int）：保存total_count相关状态、配置或数据字段。
    """
    sources: list[ProjectSourceResponse]
    total_count: int


class ProjectSourcesAddRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - sources（list[SourceReference]）：保存sources相关状态、配置或数据字段。
    """
    sources: list[SourceReference]
