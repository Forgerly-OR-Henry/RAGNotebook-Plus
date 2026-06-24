"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.models.chat_history import ChatSession
from mvc.models.document import Document
from mvc.models.note import Note
from mvc.models.project import ChatProject, ProjectSource
from mvc.schemas.projects import ProjectCreateRequest, ProjectSourceResponse, ProjectUpdateRequest
from mvc.schemas.sources import SourceReference


class ProjectService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
    """
    async def list_projects(self, db: AsyncSession, user_id: str) -> list[dict]:
        """
        用途：列出list projects相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：list[dict]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(ChatProject)
            .where(ChatProject.user_id == user_id)
            .order_by(ChatProject.updated_at.desc(), ChatProject.created_at.desc())
        )
        projects = result.scalars().all()
        return [await self._project_to_dict(db, project) for project in projects]

    async def create_project(self, db: AsyncSession, user_id: str, payload: ProjectCreateRequest) -> dict:
        """
        用途：创建create project相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（ProjectCreateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")
        project = ChatProject(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=(payload.description or "").strip() or None,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return await self._project_to_dict(db, project)

    async def get_project(self, db: AsyncSession, user_id: str, project_id: str) -> ChatProject:
        """
        用途：读取或查询get project相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。

        返回：ChatProject；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        project = await db.get(ChatProject, project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(status_code=404, detail="项目不存在")
        return project

    async def update_project(self, db: AsyncSession, user_id: str, project_id: str, payload: ProjectUpdateRequest) -> dict:
        """
        用途：更新update project相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
        - payload（ProjectUpdateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        project = await self.get_project(db, user_id, project_id)
        if payload.name is not None:
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="项目名称不能为空")
            project.name = name
        if payload.description is not None:
            project.description = payload.description.strip() or None
        await db.commit()
        await db.refresh(project)
        return await self._project_to_dict(db, project)

    async def delete_project(self, db: AsyncSession, user_id: str, project_id: str) -> None:
        """
        用途：删除delete project相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        project = await self.get_project(db, user_id, project_id)
        await db.delete(project)
        await db.commit()

    async def list_sources(self, db: AsyncSession, user_id: str, project_id: str) -> list[ProjectSourceResponse]:
        """
        用途：列出list sources相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。

        返回：list[ProjectSourceResponse]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self.get_project(db, user_id, project_id)
        result = await db.execute(
            select(ProjectSource)
            .where(ProjectSource.project_id == project_id, ProjectSource.user_id == user_id)
            .order_by(ProjectSource.created_at.desc())
        )
        sources = result.scalars().all()
        return [await self._source_to_response(db, source) for source in sources]

    async def add_sources(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: str,
        references: list[SourceReference],
    ) -> list[ProjectSourceResponse]:
        """
        用途：异步执行add sources相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
        - references（list[SourceReference]）：调用方传入的references数据或控制参数，用于驱动本函数处理流程。

        返回：list[ProjectSourceResponse]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self.get_project(db, user_id, project_id)
        refs = self._dedupe_refs(references)
        await self._validate_owned_sources(db, user_id, refs)

        for ref in refs:
            existing = await db.scalar(
                select(ProjectSource).where(
                    ProjectSource.project_id == project_id,
                    ProjectSource.user_id == user_id,
                    ProjectSource.source_type == ref.source_type,
                    ProjectSource.source_id == ref.source_id,
                )
            )
            if existing:
                continue
            db.add(
                ProjectSource(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    user_id=user_id,
                    source_type=ref.source_type,
                    source_id=ref.source_id,
                )
            )

        await db.commit()
        return await self.list_sources(db, user_id, project_id)

    async def remove_source(self, db: AsyncSession, user_id: str, project_id: str, source_type: str, source_id: str) -> None:
        """
        用途：移除remove source相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_id（str）：调用方传入的source_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self.get_project(db, user_id, project_id)
        source = await db.scalar(
            select(ProjectSource).where(
                ProjectSource.project_id == project_id,
                ProjectSource.user_id == user_id,
                ProjectSource.source_type == source_type,
                ProjectSource.source_id == source_id,
            )
        )
        if not source:
            raise HTTPException(status_code=404, detail="项目文件不存在")
        await db.delete(source)
        await db.commit()

    async def resolve_chat_references(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: str | None,
        references: list[SourceReference] | None,
        use_default_sources: bool = True,
    ) -> list[SourceReference] | None:
        """Return the effective RAG source scope for one chat turn."""
        if project_id:
            await self.get_project(db, user_id, project_id)

        if references:
            refs = self._dedupe_refs(references)
            await self._validate_owned_sources(db, user_id, refs)
            if project_id:
                await self._validate_project_contains_refs(db, user_id, project_id, refs)
            return refs

        if not use_default_sources:
            return None

        if not project_id:
            return None

        result = await db.execute(
            select(ProjectSource).where(ProjectSource.project_id == project_id, ProjectSource.user_id == user_id)
        )
        return [
            SourceReference(source_type=source.source_type, source_id=source.source_id)
            for source in result.scalars().all()
        ]

    async def _project_to_dict(self, db: AsyncSession, project: ChatProject) -> dict:
        """
        用途：异步执行project to dict相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - project（ChatProject）：调用方传入的project数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        source_count = await db.scalar(select(func.count(ProjectSource.id)).where(ProjectSource.project_id == project.id))
        session_count = await db.scalar(select(func.count(ChatSession.id)).where(ChatSession.project_id == project.id))
        return {
            "id": project.id,
            "user_id": project.user_id,
            "name": project.name,
            "description": project.description,
            "source_count": source_count or 0,
            "session_count": session_count or 0,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }

    async def _source_to_response(self, db: AsyncSession, source: ProjectSource) -> ProjectSourceResponse:
        """
        用途：异步执行source to response相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - source（ProjectSource）：调用方传入的source数据或控制参数，用于驱动本函数处理流程。

        返回：ProjectSourceResponse；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        title = "未知文件"
        preview = None
        status = None

        if source.source_type == "note":
            note = await db.get(Note, source.source_id)
            if note and note.user_id == source.user_id:
                title = note.title
                preview = note.category
        elif source.source_type == "knowledge":
            document = await db.get(Document, source.source_id)
            if document and document.user_id == source.user_id and document.source_type == "knowledge":
                title = document.title
                preview = document.status_message
                status = document.status

        return ProjectSourceResponse(
            id=source.id,
            project_id=source.project_id,
            source_type=source.source_type,
            source_id=source.source_id,
            title=title,
            preview=preview,
            status=status,
            created_at=source.created_at.isoformat() if source.created_at else None,
        )

    @staticmethod
    def _dedupe_refs(references: list[SourceReference]) -> list[SourceReference]:
        """
        用途：执行dedupe refs相关业务逻辑。

        参数：
        - references（list[SourceReference]）：调用方传入的references数据或控制参数，用于驱动本函数处理流程。

        返回：list[SourceReference]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        seen = set()
        refs: list[SourceReference] = []
        for ref in references:
            key = (ref.source_type, ref.source_id)
            if not ref.source_id or key in seen:
                continue
            seen.add(key)
            refs.append(ref)
        return refs

    async def _validate_owned_sources(self, db: AsyncSession, user_id: str, references: list[SourceReference]) -> None:
        """
        用途：校验validate owned sources相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - references（list[SourceReference]）：调用方传入的references数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        for ref in references:
            if ref.source_type == "note":
                exists = await db.scalar(select(Note.id).where(Note.id == ref.source_id, Note.user_id == user_id))
            elif ref.source_type == "knowledge":
                exists = await db.scalar(
                    select(Document.id).where(
                        Document.id == ref.source_id,
                        Document.user_id == user_id,
                        Document.source_type == "knowledge",
                    )
                )
            else:
                exists = None
            if not exists:
                raise HTTPException(status_code=404, detail=f"来源不存在: {ref.source_type}:{ref.source_id}")

    async def _validate_project_contains_refs(
        self,
        db: AsyncSession,
        user_id: str,
        project_id: str,
        references: list[SourceReference],
    ) -> None:
        """
        用途：校验validate project contains refs相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - project_id（str）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
        - references（list[SourceReference]）：调用方传入的references数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        for ref in references:
            exists = await db.scalar(
                select(ProjectSource.id).where(
                    ProjectSource.project_id == project_id,
                    ProjectSource.user_id == user_id,
                    ProjectSource.source_type == ref.source_type,
                    ProjectSource.source_id == ref.source_id,
                )
            )
            if not exists:
                raise HTTPException(status_code=400, detail=f"来源不属于当前项目: {ref.source_type}:{ref.source_id}")


_project_service: ProjectService | None = None


def get_project_service() -> ProjectService:
    """
    用途：读取或查询get project service相关的数据或流程。

    参数：无显式业务参数。

    返回：ProjectService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
