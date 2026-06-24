"""
模块职责：知识库导入服务，负责上传文件解析、存储、索引构建和进度事件输出。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import delete

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.agent_gateway.indexing_gateway import DocumentParser, IndexRepository, SSEEvent
from mvc.models.document import Document
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolderAssignment
from mvc.models.project import ProjectSource
from mvc.models.storage_object import StorageObject
from mvc.services.storage_service import StorageService, get_storage_service
from utils.env_loader import optional_env_value
from utils.magic_compat import ensure_magic_dll_path

ensure_magic_dll_path()
import magic


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_FOLDER_SIZE = 200 * 1024 * 1024
DEFAULT_PARSE_TIMEOUT_SECONDS = 120
DEFAULT_INDEX_TIMEOUT_SECONDS = 300
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".doc", ".docx", ".ppt", ".pptx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


def _timeout_seconds(env_name: str, default: float) -> float:
    """
    用途：执行timeout seconds相关业务逻辑。

    参数：
    - env_name（str）：调用方传入的env_name数据或控制参数，用于驱动本函数处理流程。
    - default（float）：调用方传入的default数据或控制参数，用于驱动本函数处理流程。

    返回：float；返回值供调用方继续编排业务流程或生成接口响应。
    """
    raw_value = optional_env_value(env_name)
    if not raw_value:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning(f"{env_name} 配置无效，使用默认值 {default} 秒")
        return default
    if value <= 0:
        logger.warning(f"{env_name} 必须大于 0，使用默认值 {default} 秒")
        return default
    return value


@dataclass
class UploadFileContent:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - filename（str）：保存filename相关状态、配置或数据字段。
    - content（bytes）：保存content相关状态、配置或数据字段。
    - file_index（int）：保存file_index相关状态、配置或数据字段。
    - file_size（int）：保存file_size相关状态、配置或数据字段。
    - mime_type（str）：保存mime_type相关状态、配置或数据字段。
    """
    filename: str
    content: bytes
    file_index: int
    file_size: int
    mime_type: str


class KnowledgeIngestionService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - parser（实例属性，由构造函数注入或初始化）：保存parser相关状态、配置或数据字段。
    - index_repository（实例属性，由构造函数注入或初始化）：保存index_repository相关状态、配置或数据字段。
    - storage_service（实例属性，由构造函数注入或初始化）：保存storage_service相关状态、配置或数据字段。
    """
    def __init__(
        self,
        parser: DocumentParser | None = None,
        index_repository: IndexRepository | None = None,
        storage_service: StorageService | None = None,
    ):
        """
        用途：执行init相关业务逻辑。

        参数：
        - parser（DocumentParser | None）：调用方传入的parser数据或控制参数，用于驱动本函数处理流程。
        - index_repository（IndexRepository | None）：调用方传入的index_repository数据或控制参数，用于驱动本函数处理流程。
        - storage_service（StorageService | None）：调用方传入的storage_service数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.parser = parser or DocumentParser()
        self.index_repository = index_repository or IndexRepository()
        self.storage_service = storage_service or get_storage_service()

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
        start_time = time.time()
        total_files = len(files)
        yield self._event("start", "开始处理文件...", total_files=total_files, progress=0)

        file_contents, validation_events = await self._read_and_validate(files)
        for event in validation_events:
            yield event

        success_count = 0
        failed_count = len(validation_events)
        for item in file_contents:
            document_id: str | None = None
            document: Document | None = None
            storage_object: StorageObject | None = None
            document_ready = False
            try:
                document_id = str(uuid.uuid4())
                content_hash = hashlib.sha256(item.content).hexdigest()
                storage_object = await self.storage_service.upload_bytes(
                    kind="knowledge",
                    user_id=user_id,
                    object_id=document_id,
                    filename=item.filename,
                    content=item.content,
                    mime_type=item.mime_type,
                )

                document = await self._create_document_record(
                    user_id=user_id,
                    document_id=document_id,
                    filename=item.filename,
                    storage_object=storage_object,
                    content_hash=content_hash,
                    file_size=item.file_size,
                    mime_type=item.mime_type,
                    status="pending",
                    status_message=None,
                    folder_id=folder_id,
                    category=category,
                )

                yield self._event(
                    "slicing_completed",
                    f"文件 {item.filename} 解析切片中...",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index - 1, total_files),
                )

                stored_content = await self.storage_service.read_object_bytes(storage_object)
                parsed = await self._with_timeout(
                    asyncio.to_thread(
                        self.parser.parse_bytes_sync,
                        content=stored_content,
                        filename=item.filename,
                        user_id=user_id,
                        use_multimodal=False,
                    ),
                    timeout_seconds=_timeout_seconds("KNOWLEDGE_PARSE_TIMEOUT_SECONDS", DEFAULT_PARSE_TIMEOUT_SECONDS),
                    timeout_message=f"文件 {item.filename} 解析超时，请稍后重试或检查文件内容",
                )

                for chunk_index, doc in enumerate(parsed.documents):
                    doc.metadata.update(
                        {
                            "document_id": document.id,
                            "filename": document.title,
                            "original_filename": storage_object.original_filename,
                            "content_hash": document.content_hash,
                            "doc_type": "knowledge",
                            "chunk_index": chunk_index,
                        }
                    )

                yield self._event(
                    "writing",
                    f"文件 {item.filename} 写入索引中...",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index - 1, total_files),
                    chunk_count=len(parsed.documents),
                    success_count=success_count,
                    failed_count=failed_count,
                )

                await self.index_repository.delete_source(user_id=user_id, source_type="knowledge", source_id=document.id)
                await self._with_timeout(
                    self.index_repository.upsert_documents(
                        source_type="knowledge",
                        source_id=document.id,
                        user_id=user_id,
                        documents=parsed.documents,
                        metadata={
                            "document_id": document.id,
                            "filename": document.title,
                            "original_filename": storage_object.original_filename,
                            "content_hash": document.content_hash,
                            "doc_type": "knowledge",
                        },
                    ),
                    timeout_seconds=_timeout_seconds("KNOWLEDGE_INDEX_TIMEOUT_SECONDS", DEFAULT_INDEX_TIMEOUT_SECONDS),
                    timeout_message=f"文件 {item.filename} 写入索引超时，请检查嵌入模型服务后重试",
                )
                await self._mark_ready(document.id, user_id, len(parsed.documents))
                if on_document_ready is not None:
                    await on_document_ready(document)
                document_ready = True
                success_count += 1
                yield self._event(
                    "completed",
                    f"文件 {item.filename} 处理完成",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index, total_files),
                    document_id=document.id,
                    chunk_count=len(parsed.documents),
                    success_count=success_count,
                    failed_count=failed_count,
                )
            except asyncio.CancelledError:
                if storage_object and document_id and not document_ready:
                    logger.warning(f"知识库文件上传连接中断，清理半成品 document_id={document_id}, filename={item.filename}")
                    await self._cleanup_partial_document(user_id=user_id, document_id=document_id, storage_object=storage_object)
                elif storage_object:
                    await self._delete_storage_object_data(storage_object, f"filename={item.filename}")
                raise
            except Exception as exc:
                failed_count += 1
                logger.error(f"知识库文件处理失败 filename={item.filename}: {exc}", exc_info=True)
                if document:
                    await self._mark_failed(document.id, user_id, str(exc))
                elif storage_object:
                    await self._delete_storage_object_data(storage_object, f"filename={item.filename}")
                yield self._event(
                    "error",
                    f"文件 {item.filename} 处理失败",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index, total_files),
                    success_count=success_count,
                    failed_count=failed_count,
                    error_message=str(exc),
                )

        elapsed = time.time() - start_time
        yield self._event(
            "finish",
            f"处理完成，成功 {success_count} 个，失败 {failed_count} 个，耗时 {elapsed:.2f} 秒",
            total_files=total_files,
            progress=100,
            success_count=success_count,
            failed_count=failed_count,
        )

    async def _read_and_validate(self, files: list[UploadFile]) -> tuple[list[UploadFileContent], list[str]]:
        """
        用途：异步执行read and validate相关业务流程。

        参数：
        - files（list[UploadFile]）：调用方传入的files数据或控制参数，用于驱动本函数处理流程。

        返回：tuple[list[UploadFileContent], list[str]]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        total_size = 0
        contents: list[UploadFileContent] = []
        events: list[str] = []
        mime = magic.Magic(mime=True)

        for index, file in enumerate(files, 1):
            content = await file.read()
            await file.seek(0)
            total_size += len(content)
            filename = file.filename or f"document-{index}"
            ext = os.path.splitext(filename)[1].lower()
            mime_type = mime.from_buffer(content)
            if len(content) > MAX_FILE_SIZE:
                events.append(self._event("error", f"文件 {filename} 超过20MB", file_index=index, filename=filename, error_message="文件大小不能超过20MB"))
                continue
            if mime_type not in ALLOWED_MIME_TYPES and ext not in ALLOWED_EXTENSIONS:
                events.append(self._event("error", f"文件 {filename} 类型不支持", file_index=index, filename=filename, error_message=f"文件类型: {mime_type}，扩展名: {ext}"))
                continue
            contents.append(
                UploadFileContent(
                    filename=filename,
                    content=content,
                    file_index=index,
                    file_size=len(content),
                    mime_type=mime_type,
                )
            )

        if total_size > MAX_FOLDER_SIZE:
            return [], [self._event("error", "文件总大小不能超过200MB", error_message="文件总大小不能超过200MB")]
        return contents, events

    async def _create_document_record(
        self,
        *,
        user_id: str,
        document_id: str,
        filename: str,
        storage_object: StorageObject,
        content_hash: str,
        file_size: int,
        mime_type: str,
        status: str,
        status_message: str | None,
        folder_id: str | None = None,
        category: str | None = None,
    ) -> Document:
        """
        用途：创建create document record相关的数据或流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - filename（str）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。
        - content_hash（str）：调用方传入的content_hash数据或控制参数，用于驱动本函数处理流程。
        - file_size（int）：调用方传入的file_size数据或控制参数，用于驱动本函数处理流程。
        - mime_type（str）：调用方传入的mime_type数据或控制参数，用于驱动本函数处理流程。
        - status（str）：调用方传入的status数据或控制参数，用于驱动本函数处理流程。
        - status_message（str | None）：调用方传入的status_message数据或控制参数，用于驱动本函数处理流程。
        - folder_id（str | None）：调用方传入的folder_id数据或控制参数，用于驱动本函数处理流程。
        - category（str | None）：调用方传入的category数据或控制参数，用于驱动本函数处理流程。

        返回：Document；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        normalized_category = category.strip() if category else None
        async with AsyncSessionLocal() as session:
            document = Document(
                id=document_id,
                user_id=user_id,
                source_type="knowledge",
                title=filename,
                storage_object_id=storage_object.id,
                content_hash=content_hash,
                file_size=file_size,
                mime_type=mime_type,
                file_ext=storage_object.file_ext,
                status=status,
                status_message=status_message,
                chunk_count=0,
            )
            knowledge_document = KnowledgeDocument(
                id=document_id,
                user_id=user_id,
                document_id=document_id,
                title=filename,
                category=normalized_category or None,
                tags=None,
            )
            session.add(storage_object)
            session.add(document)
            session.add(knowledge_document)
            if folder_id:
                session.add(
                    KnowledgeFolderAssignment(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        knowledge_id=document_id,
                        folder_id=folder_id,
                    )
                )
            try:
                await session.commit()
            except Exception:
                await self.storage_service.delete_storage_object_data(storage_object)
                raise
            await session.refresh(document)
            return document

    async def _mark_ready(self, document_id: str, user_id: str, chunk_count: int) -> None:
        """
        用途：异步执行mark ready相关业务流程。

        参数：
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - chunk_count（int）：调用方传入的chunk_count数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if document and document.user_id == user_id and document.source_type == "knowledge":
                document.status = "ready"
                document.status_message = None
                document.chunk_count = chunk_count
                await session.commit()

    async def _mark_failed(self, document_id: str, user_id: str, error: str) -> None:
        """
        用途：异步执行mark failed相关业务流程。

        参数：
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - error（str）：调用方传入的error数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if document and document.user_id == user_id and document.source_type == "knowledge":
                document.status = "failed"
                document.status_message = error
                await session.commit()

    async def _cleanup_partial_document(self, *, user_id: str, document_id: str, storage_object: StorageObject) -> None:
        """
        用途：异步执行cleanup partial document相关业务流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（str）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        try:
            await self.index_repository.delete_source(user_id=user_id, source_type="knowledge", source_id=document_id)
        except Exception as exc:
            logger.error(f"清理半成品知识库索引失败 document_id={document_id}: {exc}")

        async with AsyncSessionLocal() as session:
            await session.execute(delete(KnowledgeFolderAssignment).where(KnowledgeFolderAssignment.knowledge_id == document_id))
            await session.execute(
                delete(ProjectSource).where(
                    ProjectSource.user_id == user_id,
                    ProjectSource.source_type == "knowledge",
                    ProjectSource.source_id == document_id,
                )
            )
            await session.execute(
                delete(KnowledgeDocument).where(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.user_id == user_id,
                    KnowledgeDocument.document_id == document_id,
                )
            )
            await session.execute(
                delete(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                    Document.source_type == "knowledge",
                )
            )
            await session.execute(delete(StorageObject).where(StorageObject.id == storage_object.id))
            await session.commit()

        await self._delete_storage_object_data(storage_object, f"document_id={document_id}")

    async def _delete_storage_object_data(self, storage_object: StorageObject, context: str) -> None:
        """
        用途：删除delete storage object data相关的数据或流程。

        参数：
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。
        - context（str）：调用方传入的context数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        try:
            await self.storage_service.delete_storage_object_data(storage_object)
        except Exception as exc:
            logger.error(f"删除知识库上传文件失败 {context}: {exc}")

    @staticmethod
    async def _with_timeout(awaitable, *, timeout_seconds: float, timeout_message: str):
        """
        用途：异步执行with timeout相关业务流程。

        参数：
        - awaitable（未显式标注）：调用方传入的awaitable数据或控制参数，用于驱动本函数处理流程。
        - timeout_seconds（float）：调用方传入的timeout_seconds数据或控制参数，用于驱动本函数处理流程。
        - timeout_message（str）：调用方传入的timeout_message数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        try:
            return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
        except TimeoutError as exc:
            raise TimeoutError(timeout_message) from exc

    @staticmethod
    def _progress(current_index: int, total_files: int) -> int:
        """
        用途：执行progress相关业务逻辑。

        参数：
        - current_index（int）：调用方传入的current_index数据或控制参数，用于驱动本函数处理流程。
        - total_files（int）：调用方传入的total_files数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。
        """
        if total_files <= 0:
            return 100
        return min(99, int(current_index / total_files * 100))

    @staticmethod
    def _event(event_type: str, message: str, **kwargs) -> str:
        """
        用途：执行event相关业务逻辑。

        参数：
        - event_type（str）：调用方传入的event_type数据或控制参数，用于驱动本函数处理流程。
        - message（str）：调用方传入的message数据或控制参数，用于驱动本函数处理流程。
        - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return SSEEvent(event_type=event_type, message=message, **kwargs).to_sse()
