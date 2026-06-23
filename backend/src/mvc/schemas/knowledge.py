from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """?????????"""

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
    status: str | None = None
    status_message: str | None = None
    chunk_count: int
    preview: str
    folder_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeListResponse(BaseModel):
    """???????????"""

    documents: list[DocumentResponse]
    total_count: int


class ChunkDetail(BaseModel):
    """
    ??????????????
    images ???????????????URL????????????????
    """

    chunk_id: str
    index: int
    content: str
    page: int | None = None
    images: list[str] = Field(default_factory=list)


class DocumentDetailResponse(BaseModel):
    """
    ????????????
    ???????? chunks??????????????????? images?????????????
    ????????????????????
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
    ?????????
    images ????????????URL????"????"????????????????
    """

    chunk_id: str
    index: int
    content: str
    metadata: dict
    images: list[str] = Field(default_factory=list)


class DocumentChunksResponse(BaseModel):
    """??????????"""

    document_id: str | None = None
    filename: str
    total_chunks: int
    chunks: list[ChunkInfo]


class KnowledgeFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: str | None = None


class KnowledgeFolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    parent_id: str | None = None


class KnowledgeFolderResponse(BaseModel):
    id: str
    user_id: str
    name: str
    parent_id: str | None = None
    knowledge_count: int = 0
    children: list["KnowledgeFolderResponse"] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeFolderTreeResponse(BaseModel):
    folders: list[KnowledgeFolderResponse]
    total_count: int
    unfiled_count: int


class KnowledgeBatchFolderRequest(BaseModel):
    ids: list[str]
    folder_id: str | None = None


class KnowledgeBatchCategoryRequest(BaseModel):
    ids: list[str]
    category: str | None = None


class KnowledgeDocumentMetadataUpdate(BaseModel):
    category: str | None = None
    tags: list[str] | None = None
