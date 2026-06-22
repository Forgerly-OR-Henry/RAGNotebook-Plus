import inspect
import asyncio
from pathlib import Path

from mvc.controllers.knowledge_controller import knowledge_router
from mvc.services.sources.models import SourceChunk
from mvc.services.sources.registry import SourceRegistry
from agent.rag.rag_service import RagService


class FakeProvider:
    def __init__(self, source_type: str):
        self.source_type = source_type

    async def collect(self, db, user_id: str, source_ids: list[str], max_chunks: int):
        return [
            SourceChunk(
                source_type=self.source_type,
                source_id=f"{self.source_type}-1",
                title=f"{self.source_type} title",
                content=f"{self.source_type} content",
                chunk_id=f"{self.source_type}-chunk",
            )
        ][:max_chunks]

    async def search(self, db, user_id: str, query: str, top_k: int, source_ids: list[str] | None = None):
        return [
            SourceChunk(
                source_type=self.source_type,
                source_id=f"{self.source_type}-1",
                title=f"{self.source_type} title",
                content=query,
                chunk_id=f"{self.source_type}-chunk",
                score=0.1 if self.source_type == "note" else 0.2,
            )
        ][:top_k]


def test_domain_migration_declares_document_and_index_tables():
    migration = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260622_0001_storage_refactor_initial.py"
    text = migration.read_text(encoding="utf-8")

    assert "storage_objects" in text
    assert '"documents"' in text
    assert "index_chunks" in text
    assert "vector_chunks" not in text
    assert "knowledge_documents" not in text
    assert "knowledge_md5_records" not in text


def test_source_registry_collects_mixed_sources():
    async def scenario():
        registry = SourceRegistry([FakeProvider("note"), FakeProvider("knowledge")])

        chunks = await registry.collect(None, "user-1", "mixed", ["note-1", "knowledge-1"], max_chunks=4)

        assert [chunk.source_type for chunk in chunks] == ["note", "knowledge"]

    asyncio.run(scenario())


def test_source_registry_search_orders_by_score():
    async def scenario():
        registry = SourceRegistry([FakeProvider("knowledge"), FakeProvider("note")])

        chunks = await registry.search(None, "user-1", "query", source_type="mixed", top_k=2)

        assert [chunk.source_type for chunk in chunks] == ["note", "knowledge"]

    asyncio.run(scenario())


def test_rag_service_no_longer_reads_note_service_internal_store():
    source = inspect.getsource(RagService)

    assert "." + "notes_store" not in source
    assert "Vector" + "StoreService(" not in source


def test_knowledge_router_uses_document_id_resources():
    routes = {(route.path, method) for route in knowledge_router.routes for method in (route.methods or [])}

    assert ("/knowledge/documents", "GET") in routes
    assert ("/knowledge/documents/{document_id}", "DELETE") in routes
    assert ("/knowledge/documents/{document_id}", "GET") in routes
    assert ("/knowledge/documents/{document_id}/chunks", "GET") in routes
