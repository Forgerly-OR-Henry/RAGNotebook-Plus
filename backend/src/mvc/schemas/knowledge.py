"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """知识库文档列表项响应，描述文档元数据、索引状态、预览文本和归档位置。"""

    id: str
    document_id: str | None = None
    source_type: str = "knowledge"
    title: str | None = None
    filename: str
    original_filename: str | None = None
    user_id: str | None = None
    content_hash: str | None = None
    storage_uri: str | None = None
    file_ext: str | None = None
    mime_type: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_pinned: bool = False
    status: str | None = None
    status_message: str | None = None
    chunk_count: int
    preview: str
    folder_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeListResponse(BaseModel):
    """知识库文档列表响应，包含当前查询返回的文档集合和总数。"""

    documents: list[DocumentResponse]
    total_count: int


class ChunkDetail(BaseModel):
    """
    文档详情页使用的切片明细。

    images 保存该切片关联图片的访问 URL，供前端在正文或证据区域展示视觉来源。
    """

    chunk_id: str
    index: int
    content: str
    page: int | None = None
    images: list[str] = Field(default_factory=list)


class DocumentDetailResponse(BaseModel):
    """
    知识库文档详情响应。

    除文档元数据和完整文本外，还包含切片列表与图片资源列表，供详情页和预览页展示。
    """

    id: str
    document_id: str | None = None
    source_type: str = "knowledge"
    title: str | None = None
    filename: str
    original_filename: str | None = None
    user_id: str | None = None
    content_hash: str | None = None
    storage_uri: str | None = None
    file_ext: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_pinned: bool = False
    status: str | None = None
    status_message: str | None = None
    chunk_count: int
    content: str
    folder_id: str | None = None
    chunks: list[ChunkDetail] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class ChunkInfo(BaseModel):
    """
    文档切片接口返回的基础切片信息。

    images 保存该切片关联图片的访问 URL，便于前端展示多模态解析结果。
    """

    chunk_id: str
    index: int
    content: str
    metadata: dict
    images: list[str] = Field(default_factory=list)


class DocumentChunksResponse(BaseModel):
    """文档切片列表响应，返回文档标识、文件名、切片总数和切片明细。"""

    document_id: str | None = None
    filename: str
    total_chunks: int
    chunks: list[ChunkInfo]


class KnowledgeFolderCreate(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - name（str）：保存name相关状态、配置或数据字段。
    - parent_id（str | None）：保存parent_id相关状态、配置或数据字段。
    """
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: str | None = None


class KnowledgeFolderUpdate(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - name（str | None）：保存name相关状态、配置或数据字段。
    - parent_id（str | None）：保存parent_id相关状态、配置或数据字段。
    """
    name: str | None = Field(None, min_length=1, max_length=120)
    parent_id: str | None = None


class KnowledgeFolderResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - user_id（str）：保存user_id相关状态、配置或数据字段。
    - name（str）：保存name相关状态、配置或数据字段。
    - parent_id（str | None）：保存parent_id相关状态、配置或数据字段。
    - knowledge_count（int）：保存knowledge_count相关状态、配置或数据字段。
    - children（list["KnowledgeFolderResponse"]）：保存children相关状态、配置或数据字段。
    - created_at（str | None）：保存created_at相关状态、配置或数据字段。
    - updated_at（str | None）：保存updated_at相关状态、配置或数据字段。
    """
    id: str
    user_id: str
    name: str
    parent_id: str | None = None
    knowledge_count: int = 0
    children: list["KnowledgeFolderResponse"] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeFolderTreeResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - folders（list[KnowledgeFolderResponse]）：保存folders相关状态、配置或数据字段。
    - total_count（int）：保存total_count相关状态、配置或数据字段。
    - unfiled_count（int）：保存unfiled_count相关状态、配置或数据字段。
    """
    folders: list[KnowledgeFolderResponse]
    total_count: int
    unfiled_count: int


class KnowledgeBatchFolderRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - ids（list[str]）：保存ids相关状态、配置或数据字段。
    - folder_id（str | None）：保存folder_id相关状态、配置或数据字段。
    """
    ids: list[str]
    folder_id: str | None = None


class KnowledgeBatchCategoryRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - ids（list[str]）：保存ids相关状态、配置或数据字段。
    - category（str | None）：保存category相关状态、配置或数据字段。
    """
    ids: list[str]
    category: str | None = None


class KnowledgeDocumentMetadataUpdate(BaseModel):
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - category（str | None）：保存category相关状态、配置或数据字段。
    - tags（list[str] | None）：保存tags相关状态、配置或数据字段。
    """
    category: str | None = None
    tags: list[str] | None = None
