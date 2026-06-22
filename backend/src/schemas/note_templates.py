from pydantic import BaseModel


class NoteTemplateCreate(BaseModel):
    """创建笔记模板请求模型"""

    name: str
    icon: str = "FileText"
    category: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = []


class NoteTemplateUpdate(BaseModel):
    """更新笔记模板请求模型"""

    name: str | None = None
    icon: str | None = None
    category: str | None = None
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class NoteTemplateResponse(BaseModel):
    """笔记模板响应模型"""

    id: str
    user_id: str
    name: str
    icon: str
    category: str
    title: str
    content: str
    tags: list[str] | None = None
    is_default: bool = False
    sort_order: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class NoteTemplateReorder(BaseModel):
    """笔记模板重新排序请求模型"""

    ids: list[str]
