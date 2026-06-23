from pydantic import BaseModel, Field

from mvc.schemas.sources import SourceReference


class QueryRequest(BaseModel):
    """查询请求模型"""

    session_id: str | None = None
    project_id: str | None = None
    references: list[SourceReference] | None = None
    rag_enabled: bool = True
    query: str


class RAGRequest(BaseModel):
    """RAG检索请求模型"""

    query: str


class SessionResponse(BaseModel):
    """会话响应模型"""

    session_id: str
    project_id: str | None = None
    history: list[tuple[str, str]]


class AgentStep(BaseModel):
    """Agent执行步骤模型"""

    thought: str | None = None
    tool: str | None = None
    tool_input: dict | None = None
    tool_output: str | None = None


class AgentResponse(BaseModel):
    """Agent响应模型"""

    response: str
    session_id: str
    steps: list[AgentStep] | None = None


class RAGResponse(BaseModel):
    """RAG检索响应模型"""

    response: str


class ReorderRequest(BaseModel):
    """重排序请求模型"""

    query: str
    documents: list[str]


class ReorderResponse(BaseModel):
    """重排序响应模型"""

    documents: list[dict]


class QuizGenerateRequest(BaseModel):
    """快速测验生成请求。兼容旧前端的 selected_files/selected_notes 字段。"""

    selected_files: list[str] | None = Field(default_factory=list)
    selected_notes: list[str] | None = Field(default_factory=list)


class QuizQuestion(BaseModel):
    """快速测验题目。"""

    id: str
    type: str
    question: str
    options: list[str]
    answer: str
    explanation: str | None = None


class QuizResponse(BaseModel):
    """快速测验生成响应。"""

    title: str
    description: str | None = None
    questions: list[QuizQuestion]
