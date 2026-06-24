"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from mvc.schemas import MindMapGenerateRequest, MindMapResponse, MindMapUpdateRequest
from mvc.services.mindmap_service import MindMapService
from utils.auth_utils import get_current_user_id

mindmap_router = APIRouter(prefix="/mindmaps", tags=["mindmaps"])


def get_mindmap_service() -> MindMapService:
    """
    用途：读取或查询get mindmap service相关的数据或流程。

    参数：无显式业务参数。

    返回：MindMapService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return MindMapService()


@mindmap_router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(
    payload: MindMapGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    """
    用途：生成generate mindmap相关的数据或流程。

    参数：
    - payload（MindMapGenerateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（MindMapService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。
    - _（None）：调用方传入的_数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    try:
        data = await service.generate(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=MindMapResponse(**data))


@mindmap_router.get("/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(
    mindmap_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    """
    用途：读取或查询get mindmap相关的数据或流程。

    参数：
    - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（MindMapService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.get(db, user_id, mindmap_id)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data=MindMapResponse(**data))


@mindmap_router.put("/{mindmap_id}", response_model=MindMapResponse)
async def update_mindmap(
    mindmap_id: str,
    payload: MindMapUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    """
    用途：更新update mindmap相关的数据或流程。

    参数：
    - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。
    - payload（MindMapUpdateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（MindMapService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.update(db, user_id, mindmap_id, payload)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data=MindMapResponse(**data))


@mindmap_router.get("/{mindmap_id}/export")
async def export_mindmap(
    mindmap_id: str,
    format: str = Query("json", pattern="^(json|mermaid)$"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    """
    用途：异步执行export mindmap相关业务流程。

    参数：
    - mindmap_id（str）：调用方传入的mindmap_id数据或控制参数，用于驱动本函数处理流程。
    - format（str）：调用方传入的format数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - service（MindMapService）：调用方传入的service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    data = await service.export(db, user_id, mindmap_id, format)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data={"format": format, "content": data})
