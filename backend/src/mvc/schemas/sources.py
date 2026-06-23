from typing import Literal

from pydantic import BaseModel


SourceType = Literal["note", "knowledge", "mixed"]
SourceRefType = Literal["note", "knowledge"]
Difficulty = Literal["easy", "normal", "hard"]


class SourceReference(BaseModel):
    source_type: SourceRefType
    source_id: str


class SourceCitation(BaseModel):
    source_type: str
    source_id: str
    title: str
    chunk_id: str | None = None
    quote: str
    score: float | None = None
