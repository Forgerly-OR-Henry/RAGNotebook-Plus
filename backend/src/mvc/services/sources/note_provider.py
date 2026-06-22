from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.services.sources.models import SourceChunk
from mvc.agent_gateway.indexing_gateway import IndexRepository
from mvc.models.document import Document
from mvc.models.note import Note
from mvc.models.storage_object import StorageObject
from mvc.services.storage_service import StorageService, get_storage_service


class NoteSourceProvider:
    source_type = "note"

    def __init__(self, index_repository: IndexRepository | None = None, storage_service: StorageService | None = None):
        self.index_repository = index_repository or IndexRepository()
        self.storage_service = storage_service or get_storage_service()

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_ids: list[str],
        max_chunks: int,
    ) -> list[SourceChunk]:
        if not source_ids:
            return []
        result = await db.execute(
            select(Note, StorageObject)
            .join(Document, Note.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .where(Note.user_id == user_id, Note.id.in_(source_ids))
        )
        chunks: list[SourceChunk] = []
        for note, storage_object in result.all()[:max_chunks]:
            content = await self.storage_service.read_object_text(storage_object)
            chunks.append(
                SourceChunk(
                    source_type="note",
                    source_id=note.id,
                    title=note.title,
                    content=content,
                    chunk_id=note.id,
                )
            )
        return chunks

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        chunks = await self.index_repository.search(
            user_id=user_id,
            query=query,
            source_type="note",
            source_ids=source_ids,
            top_k=top_k,
        )
        return [
            SourceChunk(
                source_type="note",
                source_id=chunk.source_id,
                title=str(chunk.metadata.get("title") or "无标题"),
                content=chunk.content,
                chunk_id=chunk.id,
                score=chunk.score,
            )
            for chunk in chunks
        ]
