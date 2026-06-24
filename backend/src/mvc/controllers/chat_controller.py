"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import uuid

from fastapi import Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import AsyncSessionLocal, get_db
from mvc.agent_gateway.chat_gateway import stream_agent_response
from mvc.schemas import QueryRequest, QuizGenerateRequest, RAGRequest, RAGResponse, ReorderRequest, ReorderResponse, SessionResponse
from mvc.services.chat_service import ChatService, get_router_service
from mvc.services.project_service import ProjectService, get_project_service
from mvc.services.quiz_service import QuizGenerationError, QuizService, get_quiz_service
from utils.auth_utils import get_current_user_id

chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/agent/query/stream")
async def query_stream(
        request: QueryRequest,
        user_id: str = Depends(get_current_user_id),
        project_service: ProjectService = Depends(get_project_service),
        _: None = Depends(rate_limit(limit=10, window=60))
):
    """查询Agent流式响应"""
    session_id = request.session_id or str(uuid.uuid4())
    use_rag = request.rag_enabled or bool(request.references)
    async with AsyncSessionLocal() as db:
        source_refs = await project_service.resolve_chat_references(
            db,
            user_id,
            request.project_id,
            request.references,
            use_default_sources=use_rag,
        )

    return StreamingResponse(
        stream_agent_response(
            request.query,
            session_id,
            user_id,
            project_id=request.project_id,
            source_refs=source_refs,
            rag_enabled=use_rag,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@chat_router.post("/rag/query", response_model=RAGResponse)
async def query_rag(
        request: RAGRequest,
        user_id: str = Depends(get_current_user_id),
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=15, window=60))
):
    """RAG检索"""
    response = await router_service.handle_rag_query(request.query, user_id)
    return success_response(data=RAGResponse(response=response))


@chat_router.post("/quiz/generate")
async def generate_quiz(
        request: QuizGenerateRequest,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
        quiz_service: QuizService = Depends(get_quiz_service),
        _: None = Depends(rate_limit(limit=6, window=60))
):
    """根据选择的笔记或知识库文档生成快速测验。"""
    try:
        quiz = await quiz_service.generate_quiz(db, user_id, request)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=quiz)


@chat_router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """获取会话信息，使用user_id验证"""
    history = await router_service.handle_get_session(session_id, user_id)
    return success_response(data=SessionResponse(session_id=session_id, history=history))


@chat_router.delete("/session/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user_id), router_service: ChatService = Depends(get_router_service)):
    """删除会话"""
    await router_service.handle_delete_session(session_id, user_id)
    return success_response(message=f"Session {session_id} deleted successfully")


@chat_router.get("/sessions")
async def get_all_sessions(router_service: ChatService = Depends(get_router_service)):
    """获取所有会话ID"""
    session_ids = await router_service.handle_get_all_sessions()
    return success_response(data={"sessions": session_ids})


@chat_router.get("/sessions/{user_id}")
async def get_user_sessions(
    user_id: str,
    project_id: str | None = Query(None),
    current_user_id: str = Depends(get_current_user_id),
    router_service: ChatService = Depends(get_router_service),
):
    """获取用户所有会话ID"""
    session_ids = await router_service.handle_get_user_sessions(user_id, current_user_id, project_id=project_id)
    return success_response(data={"sessions": session_ids})


@chat_router.post("/reorder", response_model=ReorderResponse)
async def reorder_documents(
        request: ReorderRequest,
        router_service: ChatService = Depends(get_router_service),
        _: None = Depends(rate_limit(limit=20, window=60))
):
    """使用Ollama本地的嵌入模型对文档进行中文重排序"""
    sorted_docs = await router_service.handle_reorder(request.query, request.documents)
    return success_response(data=ReorderResponse(documents=sorted_docs))
