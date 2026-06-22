from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.services.sources.models import SourceChunk
from mvc.agent_gateway.indexing_gateway import IndexRepository
from mvc.models.document import Document


class KnowledgeSourceProvider:
    source_type = "knowledge"

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

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.source_type == "knowledge",
                Document.id.in_(source_ids),
            )
        )
        documents = {doc.id: doc for doc in result.scalars().all()}
        chunks: list[SourceChunk] = []
        for source_id in source_ids:
            document = documents.get(source_id)
            if not document:
                continue
            indexed_chunks = await self.index_repository.list_source_chunks(
                user_id=user_id,
                source_type="knowledge",
                source_id=source_id,
            )
            for chunk in indexed_chunks:
                chunks.append(
                    SourceChunk(
                        source_type="knowledge",
                        source_id=document.id,
                        title=document.title,
                        content=chunk.content,
                        chunk_id=chunk.id,
                    )
                )
                if len(chunks) >= max_chunks:
                    return chunks
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
            source_type="knowledge",
            source_ids=source_ids,
            top_k=top_k,
        )
        doc_ids = {chunk.source_id for chunk in chunks}
        if not doc_ids:
            return []

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.source_type == "knowledge",
                Document.id.in_(doc_ids),
            )
        )
        documents = {doc.id: doc for doc in result.scalars().all()}
        return [
            SourceChunk(
                source_type="knowledge",
                source_id=chunk.source_id,
                title=documents.get(chunk.source_id).title if chunk.source_id in documents else str(chunk.metadata.get("original_filename") or "知识库文档"),
                content=chunk.content,
                chunk_id=chunk.id,
                score=chunk.score,
            )
            for chunk in chunks
        ]
