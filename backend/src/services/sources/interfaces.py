from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from services.sources.models import SourceChunk


class SourceProvider(Protocol):
    source_type: str

    async def collect(
        self,
        db: AsyncSession,
        user_id: str,
        source_ids: list[str],
        max_chunks: int,
    ) -> list[SourceChunk]:
        ...

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int,
        source_ids: list[str] | None = None,
    ) -> list[SourceChunk]:
        ...
