from pydantic import BaseModel


class QueryRequest(BaseModel):
    """查询请求模型"""

    session_id: str | None = None
    query: str


class RAGRequest(BaseModel):
    """RAG检索请求模型"""

    query: str


class SessionResponse(BaseModel):
    """会话响应模型"""

    session_id: str
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
