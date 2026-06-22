from pydantic import BaseModel

from schemas.sources import Difficulty, SourceCitation, SourceType


class QuickTestCreateRequest(BaseModel):
    source_type: SourceType
    source_ids: list[str]
    question_count: int = 5
    difficulty: Difficulty = "normal"
    focus: str | None = None


class QuickTestAnswerRequest(BaseModel):
    answer: str


class QuickTestTurnResponse(BaseModel):
    id: str
    turn_index: int
    question: str
    answer: str | None = None
    feedback: str | None = None
    score: int | None = None
    citations: list[SourceCitation] = []
    created_at: str | None = None


class QuickTestSessionResponse(BaseModel):
    session_id: str
    source_type: str
    source_ids: list[str]
    question_count: int
    difficulty: str
    focus: str | None = None
    status: str
    current_turn: int
    summary: str | None = None
    weak_points: list[str] = []
    recommended_refs: list[SourceCitation] = []
    turns: list[QuickTestTurnResponse] = []
    created_at: str | None = None
    updated_at: str | None = None


class QuickTestStartResponse(BaseModel):
    session_id: str
    first_question: str
    citations: list[SourceCitation] = []


class QuickTestAnswerResponse(BaseModel):
    feedback: str
    score: int
    next_question: str | None = None
    citations: list[SourceCitation] = []
    is_finished: bool


class QuickTestFinishResponse(BaseModel):
    final_summary: str
    weak_points: list[str] = []
    recommended_notes: list[SourceCitation] = []
    recommended_documents: list[SourceCitation] = []
