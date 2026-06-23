from pydantic import BaseModel, Field

from mvc.schemas.sources import SourceReference, SourceRefType


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    source_count: int = 0
    session_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total_count: int


class ProjectSourceResponse(BaseModel):
    id: str
    project_id: str
    source_type: SourceRefType
    source_id: str
    title: str
    preview: str | None = None
    status: str | None = None
    created_at: str | None = None


class ProjectSourcesResponse(BaseModel):
    sources: list[ProjectSourceResponse]
    total_count: int


class ProjectSourcesAddRequest(BaseModel):
    sources: list[SourceReference]
