"""
模块职责：知识库业务服务，负责文档列表、分类、文件夹、预览和元数据管理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

from fastapi import UploadFile
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.agent_gateway.indexing_gateway import IndexRepository
from mvc.agent_gateway import note_ai_gateway
from mvc.models.document import Document
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolder, KnowledgeFolderAssignment
from mvc.models.project import ProjectSource
from mvc.models.storage_object import StorageObject
from mvc.schemas import (
    KnowledgeBatchCategoryRequest,
    KnowledgeBatchFolderRequest,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderResponse,
    KnowledgeFolderTreeResponse,
    KnowledgeFolderUpdate,
)
from mvc.services.document_preview_service import DocumentPreviewService, RenderedDocumentPreview
from mvc.services.knowledge_ingestion_service import KnowledgeIngestionService
from mvc.services.storage_service import StorageService, get_storage_service


class KnowledgeFolderError(ValueError):
    """Raised when a knowledge folder operation is invalid."""


class KnowledgeDocumentFileMissing(FileNotFoundError):
    """Raised when document metadata exists but its stored file is gone."""


class KnowledgeService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - storage_service（实例属性，由构造函数注入或初始化）：保存storage_service相关状态、配置或数据字段。
    - index_repository（实例属性，由构造函数注入或初始化）：保存index_repository相关状态、配置或数据字段。
    - preview_service（实例属性，由构造函数注入或初始化）：保存preview_service相关状态、配置或数据字段。
    - ingestion_service（实例属性，由构造函数注入或初始化）：保存ingestion_service相关状态、配置或数据字段。
    """
    def __init__(
        self,
        ingestion_service: KnowledgeIngestionService | None = None,
        index_repository: IndexRepository | None = None,
        storage_service: StorageService | None = None,
        preview_service: DocumentPreviewService | None = None,
    ):
        """
        用途：执行init相关业务逻辑。

        参数：
        - ingestion_service（KnowledgeIngestionService | None）：调用方传入的ingestion_service数据或控制参数，用于驱动本函数处理流程。
        - index_repository（IndexRepository | None）：调用方传入的index_repository数据或控制参数，用于驱动本函数处理流程。
        - storage_service（StorageService | None）：调用方传入的storage_service数据或控制参数，用于驱动本函数处理流程。
        - preview_service（DocumentPreviewService | None）：调用方传入的preview_service数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.storage_service = storage_service or get_storage_service()
        self.index_repository = index_repository or IndexRepository()
        self.preview_service = preview_service or DocumentPreviewService()
        self.ingestion_service = ingestion_service or KnowledgeIngestionService(
            index_repository=self.index_repository,
            storage_service=self.storage_service,
        )
    async def upload_stream(
        self,
        files: list[UploadFile],
        user_id: str,
        on_document_ready: Callable[[Document], Awaitable[None]] | None = None,
        folder_id: str | None = None,
        category: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        用途：上传upload stream相关的数据或流程。

        参数：
        - files（list[UploadFile]）：调用方传入的files数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - on_document_ready（Callable[[Document], Awaitable[None]] | None）：调用方传入的on_document_ready数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str | None）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - category（str | None）：调用方传入的category数据或控制参数，用于驱动本函数处理流程。

        返回：AsyncGenerator[str, None]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if folder_id:
            async with AsyncSessionLocal() as session:
                folder = await self._get_folder(session, user_id, folder_id)
                if not folder:
                    raise KnowledgeFolderError("文件夹不存在")

        async for event in self.ingestion_service.upload_stream(
            files,
            user_id,
            on_document_ready=on_document_ready,
            folder_id=folder_id,
            category=category,
        ):
            yield event

    async def list_documents(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str | None = None,
        unfiled: bool = False,
        category: str | None = None,
    ) -> list[dict]:
        """
        用途：列出list documents相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str | None）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - unfiled（bool）：调用方传入的unfiled数据或控制参数，用于驱动本函数处理流程。
        - category（str | None）：调用方传入的category数据或控制参数，用于驱动本函数处理流程。

        返回：list[dict]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if folder_id and unfiled:
            raise KnowledgeFolderError("folder_id 与 unfiled 不能同时使用")
        if folder_id:
            await self._ensure_folder(db, user_id, folder_id)

        stmt = (
            select(KnowledgeDocument, Document, StorageObject, KnowledgeFolderAssignment.folder_id)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .outerjoin(
                KnowledgeFolderAssignment,
                and_(
                    KnowledgeFolderAssignment.knowledge_id == KnowledgeDocument.id,
                    KnowledgeFolderAssignment.user_id == user_id,
                ),
            )
            .where(
                KnowledgeDocument.user_id == user_id,
                Document.source_type == "knowledge",
            )
        )

        if folder_id:
            stmt = stmt.where(KnowledgeFolderAssignment.folder_id == folder_id)
        elif unfiled:
            stmt = stmt.where(KnowledgeFolderAssignment.id.is_(None))
        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)

        result = await db.execute(stmt.order_by(KnowledgeDocument.is_pinned.desc(), Document.created_at.desc()))
        documents: list[dict] = []
        for knowledge_document, document, storage_object, assignment_folder_id in result.all():
            payload = self._document_to_dict(knowledge_document, document, storage_object)
            payload["folder_id"] = assignment_folder_id
            chunks = await self.index_repository.list_source_chunks(
                user_id=user_id,
                source_type="knowledge",
                source_id=document.id,
            )
            payload["preview"] = self._preview_from_chunks(chunks)
            documents.append(payload)
        return documents

    async def get_category_stats(self, db: AsyncSession, user_id: str) -> dict:
        """
        用途：读取或查询get category stats相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        category_rows = await db.execute(
            select(KnowledgeDocument.category, func.count(KnowledgeDocument.id))
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.category.isnot(None),
                Document.source_type == "knowledge",
            )
            .group_by(KnowledgeDocument.category)
        )
        categories = [{"category": category, "count": count} for category, count in category_rows.all()]

        unfiled_result = await db.execute(
            select(func.count(KnowledgeDocument.id))
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.category.is_(None),
                Document.source_type == "knowledge",
            )
        )
        total_result = await db.execute(
            select(func.count(KnowledgeDocument.id))
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(KnowledgeDocument.user_id == user_id, Document.source_type == "knowledge")
        )
        return {
            "total": int(total_result.scalar() or 0),
            "categories": categories,
            "uncategorized": int(unfiled_result.scalar() or 0),
        }

    async def delete_category(self, db: AsyncSession, user_id: str, category: str) -> int:
        """
        用途：删除delete category相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - category（str）：调用方传入的category数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(KnowledgeDocument.document_id)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.category == category,
                Document.source_type == "knowledge",
            )
        )
        document_ids = [row[0] for row in result.all()]
        deleted = 0
        for document_id in document_ids:
            if await self.delete_document(db, user_id, document_id):
                deleted += 1
        return deleted

    async def list_folders(self, db: AsyncSession, user_id: str) -> KnowledgeFolderTreeResponse:
        """
        用途：列出list folders相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：KnowledgeFolderTreeResponse；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        folder_rows = await db.execute(
            select(KnowledgeFolder)
            .where(KnowledgeFolder.user_id == user_id)
            .order_by(
                KnowledgeFolder.parent_id.asc().nullsfirst(),
                KnowledgeFolder.sort_order.asc(),
                KnowledgeFolder.created_at.asc(),
            )
        )
        folders = folder_rows.scalars().all()

        count_rows = await db.execute(
            select(KnowledgeFolderAssignment.folder_id, func.count(KnowledgeFolderAssignment.id))
            .where(KnowledgeFolderAssignment.user_id == user_id)
            .group_by(KnowledgeFolderAssignment.folder_id)
        )
        count_map = {folder_id: count for folder_id, count in count_rows.all()}

        total_result = await db.execute(
            select(func.count(KnowledgeDocument.id))
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(KnowledgeDocument.user_id == user_id, Document.source_type == "knowledge")
        )
        total_count = int(total_result.scalar() or 0)

        unfiled_result = await db.execute(
            select(func.count(KnowledgeDocument.id))
            .select_from(KnowledgeDocument)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .outerjoin(
                KnowledgeFolderAssignment,
                and_(
                    KnowledgeFolderAssignment.knowledge_id == KnowledgeDocument.id,
                    KnowledgeFolderAssignment.user_id == user_id,
                ),
            )
            .where(
                KnowledgeDocument.user_id == user_id,
                Document.source_type == "knowledge",
                KnowledgeFolderAssignment.id.is_(None),
            )
        )
        unfiled_count = int(unfiled_result.scalar() or 0)

        folder_nodes = self._build_tree(folders, count_map)
        return KnowledgeFolderTreeResponse(folders=folder_nodes, total_count=total_count, unfiled_count=unfiled_count)

    async def create_folder(self, db: AsyncSession, user_id: str, payload: KnowledgeFolderCreate) -> KnowledgeFolderResponse:
        """
        用途：创建create folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（KnowledgeFolderCreate）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：KnowledgeFolderResponse；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self._ensure_parent_folder(db, user_id, payload.parent_id)
        if await self._sibling_name_exists(db, user_id, payload.name, payload.parent_id):
            raise KnowledgeFolderError("同级目录下已存在同名文件夹")

        folder = KnowledgeFolder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            parent_id=payload.parent_id,
            name=payload.name,
            sort_order=await self._next_folder_sort_order(db, user_id, payload.parent_id),
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return self._folder_to_response(folder, 0, [])

    async def update_folder(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str,
        payload: KnowledgeFolderUpdate,
    ) -> KnowledgeFolderResponse | None:
        """
        用途：更新update folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - payload（KnowledgeFolderUpdate）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：KnowledgeFolderResponse | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            return None

        target_parent_id = payload.parent_id if payload.parent_id is not None else folder.parent_id
        target_name = payload.name if payload.name is not None else folder.name

        if payload.parent_id is not None:
            if payload.parent_id == folder.id:
                raise KnowledgeFolderError("不能将文件夹移动到自身下")
            await self._ensure_parent_folder(db, user_id, payload.parent_id)
            if await self._would_create_folder_cycle(db, user_id, folder.id, payload.parent_id):
                raise KnowledgeFolderError("不能将文件夹移动到其子孙文件夹下")

            if await self._sibling_name_exists(db, user_id, target_name, target_parent_id, exclude_id=folder.id):
                raise KnowledgeFolderError("同级目录下已存在同名文件夹")
            folder.parent_id = payload.parent_id

        if payload.name is not None:
            if await self._sibling_name_exists(db, user_id, target_name, target_parent_id, exclude_id=folder.id):
                raise KnowledgeFolderError("同级目录下已存在同名文件夹")
            folder.name = target_name

        await db.commit()
        await db.refresh(folder)
        return self._folder_to_response(folder, 0, [])

    async def delete_folder(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str,
        mode: str,
    ) -> int | None:
        """
        用途：删除delete folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - mode（str）：调用方传入的mode数据或控制参数，用于驱动本函数处理流程。

        返回：int | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            return None

        if mode not in {"unfile", "delete_documents"}:
            raise KnowledgeFolderError("mode 仅支持 unfile 或 delete_documents")

        descendant_ids = await self._descendant_folder_ids(db, user_id, folder_id)

        deleted_documents = 0
        if mode == "unfile":
            await db.execute(
                delete(KnowledgeFolderAssignment).where(
                    KnowledgeFolderAssignment.user_id == user_id,
                    KnowledgeFolderAssignment.folder_id.in_(descendant_ids),
                )
            )
        else:
            assignment_rows = await db.execute(
                select(KnowledgeFolderAssignment.knowledge_id)
                .where(
                    KnowledgeFolderAssignment.user_id == user_id,
                    KnowledgeFolderAssignment.folder_id.in_(descendant_ids),
                )
            )
            knowledge_ids = [row[0] for row in assignment_rows.all()]
            if knowledge_ids:
                doc_rows = await db.execute(
                    select(KnowledgeDocument.document_id)
                    .where(KnowledgeDocument.id.in_(knowledge_ids), KnowledgeDocument.user_id == user_id)
                )
                document_ids = [row[0] for row in doc_rows.all()]
                for document_id in document_ids:
                    await self.delete_document(db, user_id, document_id)
                deleted_documents = len(document_ids)

        await db.execute(
            delete(KnowledgeFolder)
            .where(KnowledgeFolder.user_id == user_id, KnowledgeFolder.id.in_(descendant_ids))
        )
        await db.commit()
        return deleted_documents if mode == "delete_documents" else 0

    async def batch_update_folder(
        self,
        db: AsyncSession,
        user_id: str,
        payload: KnowledgeBatchFolderRequest,
    ) -> int:
        """
        用途：异步执行batch update folder相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（KnowledgeBatchFolderRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if payload.folder_id:
            await self._ensure_folder(db, user_id, payload.folder_id)
        if not payload.ids:
            return 0

        result = await db.execute(
            select(KnowledgeDocument.id).where(KnowledgeDocument.id.in_(payload.ids), KnowledgeDocument.user_id == user_id)
        )
        knowledge_ids = [row[0] for row in result.all()]
        if not knowledge_ids:
            return 0

        await db.execute(
            delete(KnowledgeFolderAssignment).where(
                KnowledgeFolderAssignment.user_id == user_id,
                KnowledgeFolderAssignment.knowledge_id.in_(knowledge_ids),
            )
        )

        if payload.folder_id:
            for knowledge_id in knowledge_ids:
                db.add(
                    KnowledgeFolderAssignment(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        knowledge_id=knowledge_id,
                        folder_id=payload.folder_id,
                    )
                )

        await db.commit()
        return len(knowledge_ids)

    async def batch_update_category(
        self,
        db: AsyncSession,
        user_id: str,
        payload: KnowledgeBatchCategoryRequest,
    ) -> int:
        """
        用途：异步执行batch update category相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（KnowledgeBatchCategoryRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not payload.ids:
            return 0
        normalized_category = payload.category.strip() if payload.category else None
        result = await db.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id.in_(payload.ids), KnowledgeDocument.user_id == user_id)
            .values(category=normalized_category or None)
        )
        await db.commit()
        return result.rowcount or 0

    async def update_document_metadata(
        self,
        db: AsyncSession,
        user_id: str,
        document_id: str,
        payload: KnowledgeDocumentMetadataUpdate,
    ) -> dict | None:
        """
        用途：更新update document metadata相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - payload（KnowledgeDocumentMetadataUpdate）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, knowledge_document = row

        knowledge_document.category = payload.category.strip() if payload.category else None
        if payload.tags is not None:
            knowledge_document.tags = [tag.strip() for tag in payload.tags if isinstance(tag, str) and tag.strip()]
        await db.commit()
        await db.refresh(knowledge_document)

        folder_id = await self._get_knowledge_folder_id(db, user_id, knowledge_document.id)
        data = self._document_to_dict(knowledge_document, document, storage_object)
        data["folder_id"] = folder_id
        return data

    async def auto_tag_document(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        """
        用途：异步执行auto tag document相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, knowledge_document = row

        chunks = await self.index_repository.list_source_chunks(user_id=user_id, source_type="knowledge", source_id=document_id)
        source_text = "\n\n".join(part.strip() for part in [knowledge_document.title, *(chunk.content for chunk in chunks)] if part and part.strip())
        if not source_text:
            folder_id = await self._get_knowledge_folder_id(db, user_id, knowledge_document.id)
            data = self._document_to_dict(knowledge_document, document, storage_object)
            data["folder_id"] = folder_id
            return data

        result = await note_ai_gateway.generate_auto_tags(source_text[:12000])
        tags = [tag for tag in result.get("tags", []) if isinstance(tag, str) and tag.strip()]
        category = result.get("category") if isinstance(result.get("category"), str) else None
        knowledge_document.tags = tags[:5]
        if category:
            knowledge_document.category = category
        await db.commit()
        await db.refresh(knowledge_document)

        folder_id = await self._get_knowledge_folder_id(db, user_id, knowledge_document.id)
        data = self._document_to_dict(knowledge_document, document, storage_object)
        data["folder_id"] = folder_id
        return data

    async def toggle_document_pin(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        """
        用途：异步执行toggle document pin相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, knowledge_document = row

        knowledge_document.is_pinned = not bool(knowledge_document.is_pinned)
        await db.commit()
        await db.refresh(knowledge_document)

        folder_id = await self._get_knowledge_folder_id(db, user_id, knowledge_document.id)
        data = self._document_to_dict(knowledge_document, document, storage_object)
        data["folder_id"] = folder_id
        return data

    async def get_document_detail(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        """
        用途：读取或查询get document detail相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, knowledge_document = row

        chunks = await self.index_repository.list_source_chunks(user_id=user_id, source_type="knowledge", source_id=document_id)
        chunk_payloads = [self._chunk_to_dict(chunk) for chunk in chunks]
        folder_id = await self._get_knowledge_folder_id(db, user_id, knowledge_document.id)
        payload = self._document_to_dict(knowledge_document, document, storage_object)
        payload["content"] = "\n\n".join(chunk.content for chunk in chunks)
        payload["chunks"] = chunk_payloads
        payload["images"] = []
        payload["folder_id"] = folder_id
        return payload

    async def get_document_file(self, db: AsyncSession, user_id: str, document_id: str) -> tuple[Document, StorageObject, bytes] | None:
        """
        用途：读取或查询get document file相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：tuple[Document, StorageObject, bytes] | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, _ = row
        content = await self._read_stored_document_bytes(document, storage_object)
        return document, storage_object, content

    async def get_document_preview(self, db: AsyncSession, user_id: str, document_id: str) -> tuple[Document, StorageObject, RenderedDocumentPreview] | None:
        """
        用途：读取或查询get document preview相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：tuple[Document, StorageObject, RenderedDocumentPreview] | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, storage_object, _ = row
        content = await self._read_stored_document_bytes(document, storage_object)
        preview = await self.preview_service.render(
            filename=storage_object.original_filename or document.title,
            file_ext=document.file_ext or storage_object.file_ext,
            mime_type=document.mime_type or storage_object.mime_type,
            content=content,
            content_hash=document.content_hash or storage_object.checksum_sha256,
        )
        return document, storage_object, preview

    async def _read_stored_document_bytes(self, document: Document, storage_object: StorageObject) -> bytes:
        """
        用途：异步执行read stored document bytes相关业务流程。

        参数：
        - document（Document）：调用方传入的document数据或控制参数，用于驱动本函数处理流程。
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        try:
            return await self.storage_service.read_object_bytes(storage_object)
        except FileNotFoundError as exc:
            logger.warning(
                "知识库原文件不存在 document_id=%s storage_path=%s",
                document.id,
                storage_object.storage_path,
            )
            raise KnowledgeDocumentFileMissing("源文件已丢失，仅展示已解析的切片内容；建议删除该文档后重新上传。") from exc

    async def get_document_chunks(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        """
        用途：读取或查询get document chunks相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return None
        document, _, _ = row
        chunks = await self.index_repository.list_source_chunks(user_id=user_id, source_type="knowledge", source_id=document_id)
        return {
            "document_id": document.id,
            "filename": document.title,
            "total_chunks": len(chunks),
            "chunks": [self._chunk_to_dict(chunk) for chunk in chunks],
        }

    async def delete_document(self, db: AsyncSession, user_id: str, document_id: str) -> bool:
        """
        用途：删除delete document相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        row = await self._get_document_row(db, user_id, document_id)
        if not row:
            return False
        document, storage_object, knowledge_document = row

        try:
            await self.index_repository.delete_source(user_id=user_id, source_type="knowledge", source_id=document_id)
        except Exception as exc:
            logger.error(f"删除知识库索引失败 document_id={document_id}: {exc}")

        await self._delete_document_metadata(
            db=db,
            user_id=user_id,
            document_id=document.id,
            knowledge_id=knowledge_document.id,
            storage_object_id=storage_object.id,
        )
        await db.commit()

        try:
            await self.storage_service.delete_storage_object_data(storage_object)
        except Exception as exc:
            logger.error(f"删除知识库文件失败 document_id={document_id}: {exc}")
        return True

    async def clean_user_documents(self, db: AsyncSession, user_id: str) -> None:
        """
        用途：异步执行clean user documents相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(Document, StorageObject, KnowledgeDocument.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .join(KnowledgeDocument, KnowledgeDocument.document_id == Document.id)
            .where(Document.user_id == user_id, Document.source_type == "knowledge")
        )

        rows = result.all()
        storage_objects: list[StorageObject] = []
        for document, storage_object, knowledge_document_id in rows:
            try:
                await self.index_repository.delete_source(user_id=user_id, source_type="knowledge", source_id=document.id)
            except Exception as exc:
                logger.error(f"删除知识库索引失败 document_id={document.id}: {exc}")

            await self._delete_document_metadata(
                db=db,
                user_id=user_id,
                document_id=document.id,
                knowledge_id=knowledge_document_id,
                storage_object_id=storage_object.id,
            )
            storage_objects.append(storage_object)

        await db.commit()

        for storage_object in storage_objects:
            try:
                await self.storage_service.delete_storage_object_data(storage_object)
            except Exception as exc:
                logger.error(f"删除知识库文件失败 storage_object_id={storage_object.id}: {exc}")

    async def _delete_document_metadata(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        document_id: str,
        knowledge_id: str,
        storage_object_id: str,
    ) -> None:
        """
        用途：删除delete document metadata相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - knowledge_id（str）：调用方传入的knowledge_id数据或控制参数，用于驱动本函数处理流程。
        - storage_object_id（str）：调用方传入的storage_object_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await db.execute(
            delete(KnowledgeFolderAssignment).where(KnowledgeFolderAssignment.knowledge_id == knowledge_id)
        )
        await db.execute(
            delete(ProjectSource).where(
                ProjectSource.user_id == user_id,
                ProjectSource.source_type == "knowledge",
                ProjectSource.source_id == document_id,
            )
        )
        await db.execute(
            delete(KnowledgeDocument).where(
                KnowledgeDocument.id == knowledge_id,
                KnowledgeDocument.user_id == user_id,
                KnowledgeDocument.document_id == document_id,
            )
        )
        await db.execute(
            delete(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.source_type == "knowledge",
            )
        )
        await db.execute(delete(StorageObject).where(StorageObject.id == storage_object_id))

    async def _get_document_row(self, db: AsyncSession, user_id: str, document_id: str):
        """
        用途：读取或查询get document row相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(Document, StorageObject, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.source_type == "knowledge",
            )
        )
        return result.one_or_none()

    async def _get_folder(self, db: AsyncSession, user_id: str, folder_id: str | None) -> KnowledgeFolder | None:
        """
        用途：读取或查询get folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str | None）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。

        返回：KnowledgeFolder | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not folder_id:
            return None
        result = await db.execute(
            select(KnowledgeFolder).where(
                KnowledgeFolder.id == folder_id,
                KnowledgeFolder.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _ensure_folder(self, db: AsyncSession, user_id: str, folder_id: str | None) -> None:
        """
        用途：校验并确保ensure folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str | None）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not folder_id:
            return
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            raise KnowledgeFolderError("文件夹不存在")

    async def _ensure_parent_folder(self, db: AsyncSession, user_id: str, parent_id: str | None) -> None:
        """
        用途：校验并确保ensure parent folder相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - parent_id（str | None）：调用方传入的parent_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not parent_id:
            return
        parent = await self._get_folder(db, user_id, parent_id)
        if not parent:
            raise KnowledgeFolderError("父文件夹不存在")

    async def _sibling_name_exists(
        self,
        db: AsyncSession,
        user_id: str,
        name: str,
        parent_id: str | None,
        exclude_id: str | None = None,
    ) -> bool:
        """
        用途：异步执行sibling name exists相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
        - parent_id（str | None）：调用方传入的parent_id数据或控制参数，用于驱动本函数处理流程。
        - exclude_id（str | None）：调用方传入的exclude_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        conditions = [KnowledgeFolder.user_id == user_id, KnowledgeFolder.name == name]
        if parent_id:
            conditions.append(KnowledgeFolder.parent_id == parent_id)
        else:
            conditions.append(KnowledgeFolder.parent_id.is_(None))
        if exclude_id:
            conditions.append(KnowledgeFolder.id != exclude_id)
        result = await db.execute(select(func.count(KnowledgeFolder.id)).where(*conditions))
        return bool(result.scalar() or 0)

    async def _next_folder_sort_order(self, db: AsyncSession, user_id: str, parent_id: str | None) -> int:
        """
        用途：异步执行next folder sort order相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - parent_id（str | None）：调用方传入的parent_id数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        conditions = [KnowledgeFolder.user_id == user_id]
        if parent_id:
            conditions.append(KnowledgeFolder.parent_id == parent_id)
        else:
            conditions.append(KnowledgeFolder.parent_id.is_(None))
        result = await db.execute(select(func.max(KnowledgeFolder.sort_order)).where(*conditions))
        current = result.scalar()
        return int(current or 0) + 1

    async def _descendant_folder_ids(self, db: AsyncSession, user_id: str, folder_id: str) -> list[str]:
        """
        用途：异步执行descendant folder ids相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。

        返回：list[str]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(select(KnowledgeFolder.id, KnowledgeFolder.parent_id).where(KnowledgeFolder.user_id == user_id))
        children: dict[str | None, list[str]] = {}
        for current_id, parent_id in result.all():
            children.setdefault(parent_id, []).append(current_id)

        ordered: list[str] = []
        stack = [folder_id]
        while stack:
            current = stack.pop()
            ordered.append(current)
            stack.extend(children.get(current, []))
        return ordered

    async def _would_create_folder_cycle(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str,
        next_parent_id: str | None,
    ) -> bool:
        """
        用途：异步执行would create folder cycle相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - next_parent_id（str | None）：调用方传入的next_parent_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        current_parent_id = next_parent_id
        while current_parent_id:
            if current_parent_id == folder_id:
                return True
            parent = await self._get_folder(db, user_id, current_parent_id)
            current_parent_id = parent.parent_id if parent else None
        return False

    def _build_tree(self, folders: list[KnowledgeFolder], count_map: dict[str, int]) -> list[KnowledgeFolderResponse]:
        """
        用途：构建build tree相关的数据或流程。

        参数：
        - folders（list[KnowledgeFolder]）：调用方传入的folders数据或控制参数，用于驱动本函数处理流程。
        - count_map（dict[str, int]）：调用方传入的count_map数据或控制参数，用于驱动本函数处理流程。

        返回：list[KnowledgeFolderResponse]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        grouped: dict[str | None, list[KnowledgeFolder]] = {}
        for folder in folders:
            grouped.setdefault(folder.parent_id, []).append(folder)

        def walk(parent_id: str | None) -> list[KnowledgeFolderResponse]:
            """
            用途：执行walk相关业务逻辑。

            参数：
            - parent_id（str | None）：调用方传入的parent_id数据或控制参数，用于驱动本函数处理流程。

            返回：list[KnowledgeFolderResponse]；返回值供调用方继续编排业务流程或生成接口响应。
            """
            children: list[KnowledgeFolderResponse] = []
            for folder in grouped.get(parent_id, []):
                children.append(
                    self._folder_to_response(
                        folder=folder,
                        count=count_map.get(folder.id, 0),
                        children=walk(folder.id),
                    )
                )
            return children

        return walk(None)

    def _folder_to_response(
        self,
        folder: KnowledgeFolder,
        count: int,
        children: list[KnowledgeFolderResponse],
    ) -> KnowledgeFolderResponse:
        """
        用途：执行folder to response相关业务逻辑。

        参数：
        - folder（KnowledgeFolder）：调用方传入的folder数据或控制参数，用于驱动本函数处理流程。
        - count（int）：调用方传入的count数据或控制参数，用于驱动本函数处理流程。
        - children（list[KnowledgeFolderResponse]）：调用方传入的children数据或控制参数，用于驱动本函数处理流程。

        返回：KnowledgeFolderResponse；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return KnowledgeFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            parent_id=folder.parent_id,
            knowledge_count=count,
            children=children,
            created_at=str(folder.created_at) if folder.created_at else None,
            updated_at=str(folder.updated_at) if folder.updated_at else None,
        )

    async def _get_knowledge_folder_id(self, db: AsyncSession, user_id: str, knowledge_id: str) -> str | None:
        """
        用途：读取或查询get knowledge folder id相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - knowledge_id（str）：调用方传入的knowledge_id数据或控制参数，用于驱动本函数处理流程。

        返回：str | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(KnowledgeFolderAssignment.folder_id).where(
                KnowledgeFolderAssignment.user_id == user_id,
                KnowledgeFolderAssignment.knowledge_id == knowledge_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _document_to_dict(knowledge_document: KnowledgeDocument, document: Document, storage_object: StorageObject) -> dict:
        """
        用途：执行document to dict相关业务逻辑。

        参数：
        - knowledge_document（KnowledgeDocument）：调用方传入的knowledge_document数据或控制参数，用于驱动本函数处理流程。
        - document（Document）：调用方传入的document数据或控制参数，用于驱动本函数处理流程。
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return {
            "id": document.id,
            "document_id": knowledge_document.document_id,
            "source_type": document.source_type,
            "title": knowledge_document.title,
            "filename": document.title,
            "original_filename": storage_object.original_filename,
            "user_id": document.user_id,
            "content_hash": document.content_hash,
            "storage_uri": storage_object.storage_uri,
            "file_ext": document.file_ext,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "category": knowledge_document.category,
            "tags": knowledge_document.tags if knowledge_document.tags else None,
            "is_pinned": bool(knowledge_document.is_pinned),
            "status": document.status,
            "status_message": document.status_message,
            "chunk_count": document.chunk_count,
            "preview": "",
            "folder_id": None,
            "created_at": str(document.created_at) if document.created_at else None,
            "updated_at": str(document.updated_at) if document.updated_at else None,
        }

    @staticmethod
    def _preview_from_chunks(chunks) -> str:
        """
        用途：执行preview from chunks相关业务逻辑。

        参数：
        - chunks（未显式标注）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        for chunk in chunks:
            preview = " ".join((chunk.content or "").split())
            if preview:
                return preview[:220]
        return ""

    @staticmethod
    def _chunk_to_dict(chunk) -> dict:
        """
        用途：执行chunk to dict相关业务逻辑。

        参数：
        - chunk（未显式标注）：调用方传入的chunk数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return {
            "chunk_id": chunk.id,
            "index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "page": chunk.metadata.get("page"),
            "images": [],
        }


_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    """
    用途：读取或查询get knowledge service相关的数据或流程。

    参数：无显式业务参数。

    返回：KnowledgeService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
