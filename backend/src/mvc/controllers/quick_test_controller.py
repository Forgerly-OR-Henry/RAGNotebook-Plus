"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from mvc.schemas import (
    QuickTestAnswerRequest,
    QuickTestAnswerResponse,
    QuickTestCreateRequest,
    QuickTestFinishResponse,
    QuickTestSessionResponse,
    QuickTestStartResponse,
)
from mvc.services.quick_test_service import QuickTestService
from utils.auth_utils import get_current_user_id

quick_test_router = APIRouter(prefix="/quick-test", tags=["quick-test"])


def get_quick_test_service() -> QuickTestService:
    """
    用途：读取或查询get quick test service相关的数据或流程。

    参数：无显式业务参数。

    返回：QuickTestService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return QuickTestService()


@quick_test_router.post("/sessions", response_model=QuickTestStartResponse)
async def create_quick_test_session(
    payload: QuickTestCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    """
    用途：创建create quick test session相关的数据或流程。

    参数：
    - payload（QuickTestCreateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（QuickTestService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。
    - _（None）：调用方传入的_数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    try:
        data = await service.create_session(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=QuickTestStartResponse(**data))


@quick_test_router.post("/sessions/{session_id}/answer", response_model=QuickTestAnswerResponse)
async def answer_quick_test(
    session_id: str,
    payload: QuickTestAnswerRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
    _: None = Depends(rate_limit(limit=20, window=60)),
):
    """
    用途：异步执行answer quick test相关业务流程。

    参数：
    - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
    - payload（QuickTestAnswerRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（QuickTestService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。
    - _（None）：调用方传入的_数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.answer(db, user_id, session_id, payload.answer)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestAnswerResponse(**data))


@quick_test_router.get("/sessions/{session_id}", response_model=QuickTestSessionResponse)
async def get_quick_test_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
):
    """
    用途：读取或查询get quick test session相关的数据或流程。

    参数：
    - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（QuickTestService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.get_session(db, user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestSessionResponse(**data))


@quick_test_router.post("/sessions/{session_id}/finish", response_model=QuickTestFinishResponse)
async def finish_quick_test_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
):
    """
    用途：异步执行finish quick test session相关业务流程。

    参数：
    - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（QuickTestService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.finish(db, user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestFinishResponse(**data))
