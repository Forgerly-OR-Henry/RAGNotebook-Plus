"""
模块职责：FastAPI 路由控制器模块，负责请求参数绑定、权限依赖和服务层调用。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.background_init import init_manager
from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import AsyncSessionLocal, get_db
from mvc.models.document import Document
from mvc.schemas import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSourcesAddRequest,
    ProjectSourcesResponse,
    ProjectUpdateRequest,
    SourceReference,
)
from mvc.services.knowledge_service import KnowledgeService, get_knowledge_service
from mvc.services.note_service import NOTE_IMPORT_MAX_FILE_SIZE, NoteImportError
from mvc.services.project_service import ProjectService, get_project_service
from utils.auth_utils import get_current_user_id

project_router = APIRouter(prefix="/projects", tags=["projects"])


async def ensure_note_service_ready():
    """
    用途：校验并确保ensure note service ready相关的数据或流程。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    if init_manager.note_service is not None:
        return init_manager.note_service

    if init_manager.status_snapshot().get("status") == "failed":
        raise HTTPException(status_code=503, detail=init_manager.status_snapshot().get("error") or "笔记服务初始化失败")

    try:
        await asyncio.wait_for(init_manager.note_service_ready.wait(), timeout=3)
    except TimeoutError as e:
        raise HTTPException(status_code=503, detail="笔记服务仍在初始化，请稍后重试") from e

    if init_manager.note_service is None:
        raise HTTPException(status_code=503, detail="笔记服务尚未可用，请稍后重试")
    return init_manager.note_service


@project_router.get("", response_model=ProjectListResponse)
async def list_projects(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：列出list projects相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    projects = await project_service.list_projects(db, user_id)
    return success_response(data=ProjectListResponse(projects=projects, total_count=len(projects)))


@project_router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：创建create project相关的数据或流程。

    参数：
    - payload（ProjectCreateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    project = await project_service.create_project(db, user_id, payload)
    return success_response(message="项目创建成功", data=ProjectResponse(**project))


@project_router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：读取或查询get project相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    project = await project_service.get_project(db, user_id, project_id)
    return success_response(data=ProjectResponse(**await project_service._project_to_dict(db, project)))


@project_router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：更新update project相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - payload（ProjectUpdateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    project = await project_service.update_project(db, user_id, project_id, payload)
    return success_response(message="项目已更新", data=ProjectResponse(**project))


@project_router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：删除delete project相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    await project_service.delete_project(db, user_id, project_id)
    return success_response(data=None, message="项目已删除")


@project_router.get("/{project_id}/sources", response_model=ProjectSourcesResponse)
async def list_project_sources(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：列出list project sources相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    sources = await project_service.list_sources(db, user_id, project_id)
    return success_response(data=ProjectSourcesResponse(sources=sources, total_count=len(sources)))


@project_router.post("/{project_id}/sources", response_model=ProjectSourcesResponse)
async def add_project_sources(
    project_id: str,
    payload: ProjectSourcesAddRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：异步执行add project sources相关业务流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - payload（ProjectSourcesAddRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    sources = await project_service.add_sources(db, user_id, project_id, payload.sources)
    return success_response(message="项目文件已添加", data=ProjectSourcesResponse(sources=sources, total_count=len(sources)))


@project_router.delete("/{project_id}/sources/{source_type}/{source_id}")
async def remove_project_source(
    project_id: str,
    source_type: str,
    source_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
):
    """
    用途：移除remove project source相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
    - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    await project_service.remove_source(db, user_id, project_id, source_type, source_id)
    return success_response(data=None, message="项目文件已移除")


@project_router.post("/{project_id}/knowledge/documents")
async def upload_project_documents(
    project_id: str,
    files: list[UploadFile] = File(..., description="要上传到项目知识库的文件"),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    project_service: ProjectService = Depends(get_project_service),
    _: None = Depends(rate_limit(limit=3, window=60)),
):
    """
    用途：上传upload project documents相关的数据或流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - files（list[UploadFile]）：调用方传入的files数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - knowledge_service（KnowledgeService）：调用方传入的knowledge_service数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。
    - _（None）：调用方传入的_数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        await project_service.get_project(db, user_id, project_id)

    async def attach_document(document: Document) -> None:
        """
        用途：异步执行attach document相关业务流程。

        参数：
        - document（Document）：调用方传入的document数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as attach_db:
            await project_service.add_sources(
                attach_db,
                user_id,
                project_id,
                [SourceReference(source_type="knowledge", source_id=document.id)],
            )

    return StreamingResponse(
        knowledge_service.upload_stream(files, user_id, on_document_ready=attach_document),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@project_router.post("/{project_id}/notes/import")
async def import_project_note(
    project_id: str,
    file: UploadFile = File(..., description="支持 Markdown、TXT、Word 文件"),
    category: str | None = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    project_service: ProjectService = Depends(get_project_service),
    _: object = Depends(ensure_note_service_ready),
):
    """
    用途：异步执行import project note相关业务流程。

    参数：
    - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - file（UploadFile）：调用方传入的file数据或控制参数，用于驱动本函数处理流程。
    - category（str | None）：调用方传入的category数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
    - project_service（ProjectService）：调用方传入的project_service数据或控制参数，用于驱动本函数处理流程。
    - _（object）：调用方传入的_数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    await project_service.get_project(db, user_id, project_id)
    content = await file.read()
    if len(content) > NOTE_IMPORT_MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="导入文件大小不能超过 20MB")

    try:
        note = await init_manager.note_service.import_note(db, user_id, file.filename, content, category)
    except NoteImportError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    sources = await project_service.add_sources(db, user_id, project_id, [SourceReference(source_type="note", source_id=note.id)])
    return success_response(message="项目笔记导入成功", data={"note": note, "sources": sources})
