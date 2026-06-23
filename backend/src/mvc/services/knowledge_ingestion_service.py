from __future__ import annotations

import asyncio
import hashlib
import os
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass

from fastapi import UploadFile

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.agent_gateway.indexing_gateway import DocumentParser, IndexRepository, SSEEvent
from mvc.models.document import Document
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolderAssignment
from mvc.models.storage_object import StorageObject
from mvc.services.storage_service import StorageService, get_storage_service
from utils.magic_compat import ensure_magic_dll_path

ensure_magic_dll_path()
import magic


MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_FOLDER_SIZE = 200 * 1024 * 1024
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


@dataclass
class UploadFileContent:
    filename: str
    content: bytes
    file_index: int
    file_size: int
    mime_type: str


class KnowledgeIngestionService:
    def __init__(
        self,
        parser: DocumentParser | None = None,
        index_repository: IndexRepository | None = None,
        storage_service: StorageService | None = None,
    ):
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
        start_time = time.time()
        total_files = len(files)
        yield self._event("start", "开始处理文件...", total_files=total_files, progress=0)

        file_contents, validation_events = await self._read_and_validate(files)
        for event in validation_events:
            yield event

        success_count = 0
        failed_count = len(validation_events)
        for item in file_contents:
            document: Document | None = None
            storage_object: StorageObject | None = None
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
                parsed = await asyncio.to_thread(
                    self.parser.parse_bytes_sync,
                    content=stored_content,
                    filename=item.filename,
                    user_id=user_id,
                    use_multimodal=False,
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
                await self.index_repository.upsert_documents(
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
                )
                await self._mark_ready(document.id, user_id, len(parsed.documents))
                if on_document_ready is not None:
                    await on_document_ready(document)
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
            except Exception as exc:
                failed_count += 1
                logger.error(f"知识库文件处理失败 filename={item.filename}: {exc}", exc_info=True)
                if document:
                    await self._mark_failed(document.id, user_id, str(exc))
                elif storage_object:
                    await self.storage_service.delete_storage_object_data(storage_object)
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
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if document and document.user_id == user_id and document.source_type == "knowledge":
                document.status = "ready"
                document.status_message = None
                document.chunk_count = chunk_count
                await session.commit()

    async def _mark_failed(self, document_id: str, user_id: str, error: str) -> None:
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, document_id)
            if document and document.user_id == user_id and document.source_type == "knowledge":
                document.status = "failed"
                document.status_message = error
                await session.commit()

    @staticmethod
    def _progress(current_index: int, total_files: int) -> int:
        if total_files <= 0:
            return 100
        return min(99, int(current_index / total_files * 100))

    @staticmethod
    def _event(event_type: str, message: str, **kwargs) -> str:
        return SSEEvent(event_type=event_type, message=message, **kwargs).to_sse()
