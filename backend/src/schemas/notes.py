from pydantic import BaseModel


class NoteCreate(BaseModel):
    """创建笔记请求模型"""

    title: str
    content: str
    category: str | None = None
    tags: list[str] | None = None


class NoteUpdate(BaseModel):
    """更新笔记请求模型（所有字段可选）"""

    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_pinned: bool | None = None


class NoteResponse(BaseModel):
    """笔记响应模型"""

    id: str
    user_id: str
    title: str
    content: str
    tags: list[str] | None = None
    category: str | None = None
    is_pinned: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class NoteListResponse(BaseModel):
    """笔记列表响应模型"""

    notes: list[NoteResponse]
    total_count: int


class NoteSearchRequest(BaseModel):
    """笔记搜索请求模型"""

    query: str


class RelatedNoteItem(BaseModel):
    """关联笔记项模型"""

    id: str
    title: str
    content_preview: str
    similarity: float
    source: str


class RelatedNotesResponse(BaseModel):
    """关联笔记列表响应模型"""

    notes: list[RelatedNoteItem]


class PageRequest(BaseModel):
    """分页请求模型"""

    page: int = 1
    page_size: int = 20
    category: str | None = None
    tag: str | None = None


class BatchIdsRequest(BaseModel):
    """批量操作请求模型（按 ID 列表）"""

    ids: list[str]


class BatchCategoryRequest(BaseModel):
    """批量更新分类请求模型"""

    ids: list[str]
    category: str


class BatchPinRequest(BaseModel):
    """批量置顶请求模型"""

    ids: list[str]
    is_pinned: bool
