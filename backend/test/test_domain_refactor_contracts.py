import inspect
import asyncio

from mvc.controllers.knowledge_controller import knowledge_router
from db import db_config
from mvc.models.base import Base
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolder, KnowledgeFolderAssignment
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


def test_current_schema_declares_document_and_index_tables():
    db_config._import_all_models()

    assert "storage_objects" in Base.metadata.tables
    assert "documents" in Base.metadata.tables
    assert "notes" in Base.metadata.tables
    assert KnowledgeDocument.__tablename__ == "knowledge_documents"
    assert KnowledgeFolder.__tablename__ == "knowledge_folders"
    assert KnowledgeFolderAssignment.__tablename__ == "knowledge_folder_assignments"
    assert {"knowledge_documents", "knowledge_folders", "knowledge_folder_assignments"} <= set(Base.metadata.tables)
    assert db_config.INDEX_CHUNKS_TABLE == "index_chunks"
    assert db_config.INDEX_CHUNKS_COLUMNS >= {
        "document_id",
        "source_type",
        "content_hash",
        "embedding",
    }


def test_current_schema_rejects_legacy_tables():
    unsupported = db_config._unsupported_schema_tables({"notes", "user_service", "legacy_version"})

    assert unsupported == {"user_service", "legacy_version"}


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
    assert ("/knowledge/documents/{document_id}/file", "GET") in routes
    assert ("/knowledge/documents/{document_id}/preview", "GET") in routes
    assert ("/knowledge/documents/{document_id}/chunks", "GET") in routes
    assert ("/knowledge/documents/{document_id}/metadata", "PUT") in routes
    assert ("/knowledge/documents/{document_id}/auto-tag", "POST") in routes
    assert ("/knowledge/folders", "GET") in routes
    assert ("/knowledge/folders", "POST") in routes
    assert ("/knowledge/folders/{folder_id}", "PUT") in routes
    assert ("/knowledge/folders/{folder_id}", "DELETE") in routes
    assert ("/knowledge/batch/folder", "PUT") in routes
    assert ("/knowledge/batch/category", "PUT") in routes
    assert ("/knowledge/stats", "GET") in routes
    assert ("/knowledge/category/{category}", "DELETE") in routes
