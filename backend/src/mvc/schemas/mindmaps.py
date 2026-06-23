from pydantic import BaseModel, Field

from mvc.schemas.sources import SourceCitation, SourceRefType


class MindMapGenerateRequest(BaseModel):
    source_type: SourceRefType
    source_ids: list[str] = Field(min_length=1, max_length=20)
    max_nodes: int = 40
    max_depth: int = 4
    focus: str | None = None


class MindMapNode(BaseModel):
    id: str
    label: str
    level: int = 0
    type: str = "concept"
    summary: str | None = None
    source_refs: list[str] = []


class MindMapEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class MindMapResponse(BaseModel):
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
    title: str
    nodes: list[MindMapNode]
    edges: list[MindMapEdge]
