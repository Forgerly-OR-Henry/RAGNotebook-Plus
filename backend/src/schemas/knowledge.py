from pydantic import BaseModel


class KnowledgeDocument(BaseModel):
    """知识库文档信息模型"""

    id: str
    document_id: str | None = None
    filename: str
    original_filename: str | None = None
    user_id: str | None = None
    md5: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    status: str | None = None
    status_message: str | None = None
    chunk_count: int
    preview: str
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeListResponse(BaseModel):
    """知识库文档列表响应模型"""

    documents: list[KnowledgeDocument]
    total_count: int


class ChunkDetail(BaseModel):
    """
    文档切片详情（含对应图片）。
    images 字段保存该切片所涉及的所有图片URL，前端可据此在切片旁边展示图片。
    """

    chunk_id: str
    index: int
    content: str
    page: int | None = None
    images: list[str] = []


class KnowledgeDocumentDetail(BaseModel):
    """
    知识库文档详情响应模型。
    相比旧版本新增了 chunks（切片级详情，包含每段文本对应的图片）和 images（文档全量图片列表）字段，
    前端可以在文档详情页同时展示文本和图片。
    """

    id: str
    document_id: str | None = None
    filename: str
    original_filename: str | None = None
    user_id: str | None = None
    md5: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    status: str | None = None
    status_message: str | None = None
    chunk_count: int
    content: str
    chunks: list[ChunkDetail] = []
    images: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class ChunkInfo(BaseModel):
    """
    文档切片信息模型。
    images 字段保存该切片关联的图片URL，前端在"查看切片"页面中可以按切片展示对应的图片。
    """

    chunk_id: str
    index: int
    content: str
    metadata: dict
    images: list[str] = []


class DocumentChunksResponse(BaseModel):
    """文档切片列表响应模型"""

    document_id: str | None = None
    filename: str
    total_chunks: int
    chunks: list[ChunkInfo]


class MD5Record(BaseModel):
    """MD5记录模型"""

    md5: str
    filename: str | None = None
    original_filename: str | None = None
    upload_time: str | None = None


class MD5ListResponse(BaseModel):
    """MD5记录列表响应模型"""

    records: list[MD5Record]
    total_count: int
