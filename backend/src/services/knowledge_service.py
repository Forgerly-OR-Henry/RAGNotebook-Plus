from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from repositories.document_parser import DocumentParser
from repositories.index_repository import IndexRepository
from models.knowledge_document import KnowledgeDocument
from ai.rag.sse_models import SSEEvent
from utils.image_extractor import delete_image_directory, delete_user_all_images, get_image_storage_dir
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
    def __init__(self, parser: DocumentParser | None = None, index_repository: IndexRepository | None = None):
        self.parser = parser or DocumentParser()
        self.index_repository = index_repository or IndexRepository()

    async def upload_stream(self, files: list[UploadFile], user_id: str) -> AsyncGenerator[str, None]:
        start_time = time.time()
        total_files = len(files)
        yield self._event("start", "开始处理文件...", total_files=total_files, progress=0)

        file_contents, validation_events = await self._read_and_validate(files)
        for event in validation_events:
            yield event

        success_count = 0
        failed_count = len(validation_events)
        for item in file_contents:
            try:
                yield self._event(
                    "slicing_completed",
                    f"文件 {item.filename} 解析切片中...",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index - 1, total_files),
                )
                parsed = await asyncio.to_thread(
                    self.parser.parse_bytes_sync,
                    content=item.content,
                    filename=item.filename,
                    user_id=user_id,
                    use_multimodal=False,
                )
                document = await self._upsert_document_record(
                    user_id=user_id,
                    filename=item.filename,
                    md5=parsed.md5,
                    file_size=item.file_size,
                    mime_type=item.mime_type,
                    status="processing",
                    status_message=None,
                )

                for chunk_index, doc in enumerate(parsed.documents):
                    doc.metadata.update(
                        {
                            "document_id": document.id,
                            "filename": document.filename,
                            "original_filename": document.original_filename,
                            "md5": document.md5,
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
                        "filename": document.filename,
                        "original_filename": document.original_filename,
                        "md5": document.md5,
                        "doc_type": "knowledge",
                    },
                )
                await self._mark_ready(document.id, user_id, len(parsed.documents))
                success_count += 1
                yield self._event(
                    "completed",
                    f"文件 {item.filename} 处理完成",
                    total_files=total_files,
                    file_index=item.file_index,
                    filename=item.filename,
                    progress=self._progress(item.file_index, total_files),
                    chunk_count=len(parsed.documents),
                    success_count=success_count,
                    failed_count=failed_count,
                )
            except Exception as exc:
                failed_count += 1
                logger.error(f"知识库文件处理失败 filename={item.filename}: {exc}", exc_info=True)
                await self._mark_failed_by_md5(user_id, hashlib.md5(item.content).hexdigest(), str(exc))
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
            contents.append(UploadFileContent(filename=filename, content=content, file_index=index, file_size=len(content), mime_type=mime_type))

        if total_size > MAX_FOLDER_SIZE:
            return [], [self._event("error", "文件总大小不能超过200MB", error_message="文件总大小不能超过200MB")]
        return contents, events

    async def _upsert_document_record(
        self,
        *,
        user_id: str,
        filename: str,
        md5: str,
        file_size: int,
        mime_type: str,
        status: str,
        status_message: str | None,
    ) -> KnowledgeDocument:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user_id, KnowledgeDocument.md5 == md5))
            document = result.scalar_one_or_none()
            if document is None:
                document = KnowledgeDocument(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    filename=filename,
                    original_filename=filename,
                    md5=md5,
                    file_size=file_size,
                    mime_type=mime_type,
                    status=status,
                    status_message=status_message,
                    chunk_count=0,
                )
                session.add(document)
            else:
                document.filename = filename
                document.original_filename = filename
                document.file_size = file_size
                document.mime_type = mime_type
                document.status = status
                document.status_message = status_message
            await session.commit()
            await session.refresh(document)
            return document

    async def _mark_ready(self, document_id: str, user_id: str, chunk_count: int) -> None:
        async with AsyncSessionLocal() as session:
            document = await session.get(KnowledgeDocument, document_id)
            if document and document.user_id == user_id:
                document.status = "ready"
                document.status_message = None
                document.chunk_count = chunk_count
                await session.commit()

    async def _mark_failed_by_md5(self, user_id: str, md5: str, error: str) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user_id, KnowledgeDocument.md5 == md5))
            document = result.scalar_one_or_none()
            if document:
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


class KnowledgeService:
    def __init__(self, ingestion_service: KnowledgeIngestionService | None = None, index_repository: IndexRepository | None = None):
        self.ingestion_service = ingestion_service or KnowledgeIngestionService()
        self.index_repository = index_repository or IndexRepository()

    async def upload_stream(self, files: list[UploadFile], user_id: str) -> AsyncGenerator[str, None]:
        async for event in self.ingestion_service.upload_stream(files, user_id):
            yield event

    async def list_documents(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.user_id == user_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return [self._document_to_dict(document) for document in result.scalars().all()]

    async def get_document_detail(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        document = await db.get(KnowledgeDocument, document_id)
        if not document or document.user_id != user_id:
            return None
        chunks = await self.index_repository.list_source_chunks(user_id=user_id, source_type="knowledge", source_id=document_id)
        chunk_payloads = [self._chunk_to_dict(document, chunk) for chunk in chunks]
        images = []
        for chunk in chunk_payloads:
            images.extend(chunk.get("images", []))
        return {
            **self._document_to_dict(document),
            "content": "\n\n".join(chunk.content for chunk in chunks),
            "chunks": chunk_payloads,
            "images": list(dict.fromkeys(images)),
        }

    async def get_document_chunks(self, db: AsyncSession, user_id: str, document_id: str) -> dict | None:
        document = await db.get(KnowledgeDocument, document_id)
        if not document or document.user_id != user_id:
            return None
        chunks = await self.index_repository.list_source_chunks(user_id=user_id, source_type="knowledge", source_id=document_id)
        return {
            "document_id": document.id,
            "filename": document.filename,
            "total_chunks": len(chunks),
            "chunks": [self._chunk_to_dict(document, chunk) for chunk in chunks],
        }

    async def delete_document(self, db: AsyncSession, user_id: str, document_id: str) -> bool:
        document = await db.get(KnowledgeDocument, document_id)
        if not document or document.user_id != user_id:
            return False
        await self.index_repository.delete_source(user_id=user_id, source_type="knowledge", source_id=document_id)
        if document.md5:
            delete_image_directory(user_id, document.md5)
        await db.delete(document)
        await db.commit()
        return True

    async def delete_by_filename(self, db: AsyncSession, user_id: str, filename: str) -> bool:
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.user_id == user_id,
                or_(KnowledgeDocument.filename == filename, KnowledgeDocument.original_filename == filename),
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False
        return await self.delete_document(db, user_id, document.id)

    async def clean_user_documents(self, db: AsyncSession, user_id: str) -> None:
        await self.index_repository.delete_user_source_type(user_id=user_id, source_type="knowledge")
        await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.user_id == user_id))
        await db.commit()
        delete_user_all_images(user_id)

    async def get_document_by_md5(self, db: AsyncSession, user_id: str, md5: str) -> dict | None:
        result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user_id, KnowledgeDocument.md5 == md5))
        document = result.scalar_one_or_none()
        return self._document_to_dict(document) if document else None

    async def list_md5_records(self, db: AsyncSession, user_id: str) -> list[dict]:
        result = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.user_id == user_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return [
            {
                "md5": document.md5,
                "filename": document.filename,
                "original_filename": document.original_filename,
                "upload_time": str(document.created_at) if document.created_at else None,
            }
            for document in result.scalars().all()
        ]

    async def get_batch_images(self, user_id: str, md5: str) -> dict:
        image_dir = get_image_storage_dir(user_id, md5)
        if not os.path.exists(image_dir):
            return {"images": [], "count": 0}
        images = []
        for filename in os.listdir(image_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                image_path = os.path.join(image_dir, filename)
                with open(image_path, "rb") as handle:
                    encoded = base64.b64encode(handle.read()).decode("utf-8")
                images.append({"filename": filename, "data": encoded})
        return {"images": images, "count": len(images)}

    @staticmethod
    def _document_to_dict(document: KnowledgeDocument) -> dict:
        return {
            "id": document.id,
            "document_id": document.id,
            "filename": document.filename,
            "original_filename": document.original_filename,
            "user_id": document.user_id,
            "md5": document.md5,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "status": document.status,
            "status_message": document.status_message,
            "chunk_count": document.chunk_count,
            "preview": "",
            "created_at": str(document.created_at) if document.created_at else None,
            "updated_at": str(document.updated_at) if document.updated_at else None,
        }

    @staticmethod
    def _chunk_to_dict(document: KnowledgeDocument, chunk) -> dict:
        image_paths = chunk.metadata.get("image_paths") or chunk.metadata.get("images") or []
        if not isinstance(image_paths, list):
            image_paths = []
        images = [f"/knowledge/image/{document.md5}/{os.path.basename(path)}" for path in image_paths]
        return {
            "chunk_id": chunk.id,
            "index": chunk.chunk_index,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "page": chunk.metadata.get("page"),
            "images": images,
        }


_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
