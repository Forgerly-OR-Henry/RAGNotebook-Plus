"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from pydantic import BaseModel

from mvc.schemas.sources import Difficulty, SourceCitation, SourceType


class QuickTestCreateRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - source_type（SourceType）：保存source_type相关状态、配置或数据字段。
    - source_ids（list[str]）：保存source_ids相关状态、配置或数据字段。
    - question_count（int）：保存question_count相关状态、配置或数据字段。
    - difficulty（Difficulty）：保存difficulty相关状态、配置或数据字段。
    - focus（str | None）：保存focus相关状态、配置或数据字段。
    """
    source_type: SourceType
    source_ids: list[str]
    question_count: int = 5
    difficulty: Difficulty = "normal"
    focus: str | None = None


class QuickTestAnswerRequest(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - answer（str）：保存answer相关状态、配置或数据字段。
    """
    answer: str


class QuickTestTurnResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - id（str）：保存id相关状态、配置或数据字段。
    - turn_index（int）：保存turn_index相关状态、配置或数据字段。
    - question（str）：保存question相关状态、配置或数据字段。
    - answer（str | None）：保存answer相关状态、配置或数据字段。
    - feedback（str | None）：保存feedback相关状态、配置或数据字段。
    - score（int | None）：保存score相关状态、配置或数据字段。
    - citations（list[SourceCitation]）：保存citations相关状态、配置或数据字段。
    - created_at（str | None）：保存created_at相关状态、配置或数据字段。
    """
    id: str
    turn_index: int
    question: str
    answer: str | None = None
    feedback: str | None = None
    score: int | None = None
    citations: list[SourceCitation] = []
    created_at: str | None = None


class QuickTestSessionResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - session_id（str）：保存session_id相关状态、配置或数据字段。
    - source_type（str）：保存source_type相关状态、配置或数据字段。
    - source_ids（list[str]）：保存source_ids相关状态、配置或数据字段。
    - question_count（int）：保存question_count相关状态、配置或数据字段。
    - difficulty（str）：保存difficulty相关状态、配置或数据字段。
    - focus（str | None）：保存focus相关状态、配置或数据字段。
    - status（str）：保存status相关状态、配置或数据字段。
    - current_turn（int）：保存current_turn相关状态、配置或数据字段。
    - summary（str | None）：保存summary相关状态、配置或数据字段。
    - weak_points（list[str]）：保存weak_points相关状态、配置或数据字段。
    - recommended_refs（list[SourceCitation]）：保存recommended_refs相关状态、配置或数据字段。
    - turns（list[QuickTestTurnResponse]）：保存turns相关状态、配置或数据字段。
    - created_at（str | None）：保存created_at相关状态、配置或数据字段。
    - updated_at（str | None）：保存updated_at相关状态、配置或数据字段。
    """
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
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - session_id（str）：保存session_id相关状态、配置或数据字段。
    - first_question（str）：保存first_question相关状态、配置或数据字段。
    - citations（list[SourceCitation]）：保存citations相关状态、配置或数据字段。
    """
    session_id: str
    first_question: str
    citations: list[SourceCitation] = []


class QuickTestAnswerResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - feedback（str）：保存feedback相关状态、配置或数据字段。
    - score（int）：保存score相关状态、配置或数据字段。
    - next_question（str | None）：保存next_question相关状态、配置或数据字段。
    - citations（list[SourceCitation]）：保存citations相关状态、配置或数据字段。
    - is_finished（bool）：保存is_finished相关状态、配置或数据字段。
    """
    feedback: str
    score: int
    next_question: str | None = None
    citations: list[SourceCitation] = []
    is_finished: bool


class QuickTestFinishResponse(BaseModel):
    """
    用途：接口数据模型，用于描述请求/响应字段和类型约束。

    属性：
    - final_summary（str）：保存final_summary相关状态、配置或数据字段。
    - weak_points（list[str]）：保存weak_points相关状态、配置或数据字段。
    - recommended_notes（list[SourceCitation]）：保存recommended_notes相关状态、配置或数据字段。
    - recommended_documents（list[SourceCitation]）：保存recommended_documents相关状态、配置或数据字段。
    """
    final_summary: str
    weak_points: list[str] = []
    recommended_notes: list[SourceCitation] = []
    recommended_documents: list[SourceCitation] = []
