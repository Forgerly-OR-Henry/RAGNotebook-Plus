from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from services.sources.interfaces import SourceProvider
from services.sources.models import SourceChunk


class SourceRegistry:
    def __init__(self, providers: list[SourceProvider]):
        self.providers = {provider.source_type: provider for provider in providers}

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_type: str,
        source_ids: list[str],
        max_chunks: int = 12,
    ) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []
        normalized_ids = [sid for sid in source_ids if sid]
        for provider in self._providers_for(source_type):
            chunks.extend(await provider.collect(db, user_id, normalized_ids, max_chunks=max_chunks))
            if len(chunks) >= max_chunks:
                break
        return chunks[:max_chunks]

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        source_type: str = "mixed",
        top_k: int = 6,
        source_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []
        for provider in self._providers_for(source_type):
            chunks.extend(await provider.search(db, user_id, query, top_k=top_k, source_ids=source_ids))
        chunks.sort(key=lambda chunk: chunk.score if chunk.score is not None else 999999.0)
        return chunks[:top_k]

    def _providers_for(self, source_type: str) -> list[SourceProvider]:
        if source_type == "mixed":
            return [self.providers[key] for key in ("note", "knowledge") if key in self.providers]
        provider = self.providers.get(source_type)
        return [provider] if provider else []


_source_registry: SourceRegistry | None = None


def get_source_registry() -> SourceRegistry:
    global _source_registry
    if _source_registry is None:
        from services.sources.knowledge_provider import KnowledgeSourceProvider
        from services.sources.note_provider import NoteSourceProvider

        _source_registry = SourceRegistry([NoteSourceProvider(), KnowledgeSourceProvider()])
    return _source_registry
