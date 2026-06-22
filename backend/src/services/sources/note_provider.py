from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.sources.models import SourceChunk
from repositories.index_repository import IndexRepository
from models.note import Note


class NoteSourceProvider:
    source_type = "note"

    def __init__(self, index_repository: IndexRepository | None = None):
        self.index_repository = index_repository or IndexRepository()

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_ids: list[str],
        max_chunks: int,
    ) -> list[SourceChunk]:
        if not source_ids:
            return []
        result = await db.execute(select(Note).where(Note.user_id == user_id, Note.id.in_(source_ids)))
        notes = result.scalars().all()
        return [
            SourceChunk(
                source_type="note",
                source_id=note.id,
                title=note.title,
                content=note.content,
                chunk_id=note.id,
            )
            for note in notes[:max_chunks]
        ]

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
