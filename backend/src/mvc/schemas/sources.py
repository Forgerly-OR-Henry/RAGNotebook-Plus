from typing import Literal

from pydantic import BaseModel


SourceType = Literal["note", "knowledge", "mixed"]
Difficulty = Literal["easy", "normal", "hard"]


class SourceCitation(BaseModel):
    source_type: str
    source_id: str
    title: str
    chunk_id: str | None = None
    quote: str
    score: float | None = None
