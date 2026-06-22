from mvc.services.sources import SourceChunk, SourceRegistry, format_source_context, get_source_registry


class SourceCollector:
    """Backward-compatible adapter over the domain source registry."""

    async def collect(self, db, user_id: str, source_type: str, source_ids: list[str], max_chunks: int = 12) -> list[SourceChunk]:
        return await get_source_registry().collect(db, user_id, source_type, source_ids, max_chunks=max_chunks)


__all__ = ["SourceChunk", "SourceCollector", "SourceRegistry", "format_source_context", "get_source_registry"]
