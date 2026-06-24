from starlette.routing import Match

from mvc.controllers.knowledge_controller import knowledge_router
from mvc.models.document import Document
from mvc.models.base import Base
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolder, KnowledgeFolderAssignment
from mvc.models.storage_object import StorageObject
from mvc.schemas import (
    KnowledgeBatchCategoryRequest,
    KnowledgeBatchFolderRequest,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderUpdate,
)
from mvc.services.knowledge_service import KnowledgeService


def _matched_endpoint(path: str, method: str) -> str:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
        "root_path": "",
    }

    for route in knowledge_router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.endpoint.__name__
    raise AssertionError(f"{method} {path} did not match any route")


def test_knowledge_folder_schema_contract():
    assert KnowledgeDocument.__tablename__ == "knowledge_documents"
    assert KnowledgeFolder.__tablename__ == "knowledge_folders"
    assert KnowledgeFolderAssignment.__tablename__ == "knowledge_folder_assignments"
    assert {"knowledge_documents", "knowledge_folders", "knowledge_folder_assignments"} <= set(Base.metadata.tables)
    assert "uq_knowledge_folder_sibling_name" in {
        constraint.name for constraint in KnowledgeFolder.__table__.constraints
    }
    assert "uq_knowledge_folder_assignment_knowledge" in {
        constraint.name for constraint in KnowledgeFolderAssignment.__table__.constraints
    }
    assert KnowledgeDocument.__table__.columns["is_pinned"].default is not None


def test_knowledge_folder_request_contracts():
    payload = KnowledgeFolderCreate(name="项目")
    update = KnowledgeFolderUpdate(name="归档", parent_id="parent-id")
    batch = KnowledgeBatchFolderRequest(ids=["doc-1", "doc-2"], folder_id="folder-1")
    category = KnowledgeBatchCategoryRequest(ids=["doc-1"], category="work")
    metadata = KnowledgeDocumentMetadataUpdate(category="study", tags=["AI", "RAG"])

    assert payload.name == "项目"
    assert update.parent_id == "parent-id"
    assert batch.ids == ["doc-1", "doc-2"]
    assert batch.folder_id == "folder-1"
    assert category.category == "work"
    assert metadata.tags == ["AI", "RAG"]


def test_knowledge_folder_routes_contract():
    assert _matched_endpoint("/knowledge/folders", "GET") == "list_knowledge_folders"
    assert _matched_endpoint("/knowledge/folders", "POST") == "create_knowledge_folder"
    assert _matched_endpoint("/knowledge/folders/folder-1", "PUT") == "update_knowledge_folder"
    assert _matched_endpoint("/knowledge/folders/folder-1", "DELETE") == "delete_knowledge_folder"
    assert _matched_endpoint("/knowledge/batch/folder", "PUT") == "batch_update_knowledge_folder"
    assert _matched_endpoint("/knowledge/batch/category", "PUT") == "batch_update_knowledge_category"
    assert _matched_endpoint("/knowledge/documents/doc-1/metadata", "PUT") == "update_document_metadata"
    assert _matched_endpoint("/knowledge/documents/doc-1/auto-tag", "POST") == "auto_tag_document"
    assert _matched_endpoint("/knowledge/documents/doc-1/pin", "PUT") == "toggle_document_pin"
    assert _matched_endpoint("/knowledge/stats", "GET") == "get_knowledge_stats"
    assert _matched_endpoint("/knowledge/category/work", "DELETE") == "delete_knowledge_category"


def test_delete_document_removes_visible_records_when_index_cleanup_fails(monkeypatch):
    events = []

    class FailingIndexRepository:
        async def delete_source(self, **kwargs):
            raise RuntimeError("index unavailable")

    class FakeStorageService:
        def __init__(self):
            self.deleted_paths = []

        async def delete_storage_object_data(self, storage_object):
            events.append(("storage_delete", storage_object.storage_path))
            self.deleted_paths.append(storage_object.storage_path)

    class FakeDb:
        def __init__(self):
            self.executed = []
            self.deleted = []
            self.committed = False

        async def execute(self, statement):
            events.append(("execute", statement.table.name))
            self.executed.append(statement)

        async def delete(self, item):
            self.deleted.append(item)

        async def commit(self):
            events.append(("commit", None))
            self.committed = True

    document = Document(
        id="doc-1",
        user_id="user-1",
        source_type="knowledge",
        title="rag_release_notes.md",
        storage_object_id="doc-1",
        content_hash="hash",
        file_size=100,
        status="ready",
    )
    storage_object = StorageObject(
        id="doc-1",
        backend="local",
        host="local",
        storage_uri="local://knowledge/user-1/doc-1.md",
        storage_path="knowledge/user-1/doc-1.md",
        original_filename="rag_release_notes.md",
        checksum_sha256="hash",
        size_bytes=100,
    )
    knowledge_document = KnowledgeDocument(
        id="doc-1",
        user_id="user-1",
        document_id="doc-1",
        title="rag_release_notes.md",
    )

    storage_service = FakeStorageService()
    service = KnowledgeService(index_repository=FailingIndexRepository(), storage_service=storage_service)

    async def fake_get_document_row(db, user_id, document_id):
        return document, storage_object, knowledge_document

    monkeypatch.setattr(service, "_get_document_row", fake_get_document_row)

    import asyncio

    db = FakeDb()
    assert asyncio.run(service.delete_document(db, "user-1", "doc-1")) is True
    assert db.committed is True
    assert db.deleted == []
    assert [statement.table.name for statement in db.executed] == [
        "knowledge_folder_assignments",
        "project_sources",
        "knowledge_documents",
        "documents",
        "storage_objects",
    ]
    assert events == [
        ("execute", "knowledge_folder_assignments"),
        ("execute", "project_sources"),
        ("execute", "knowledge_documents"),
        ("execute", "documents"),
        ("execute", "storage_objects"),
        ("commit", None),
        ("storage_delete", "knowledge/user-1/doc-1.md"),
    ]
    assert storage_service.deleted_paths == ["knowledge/user-1/doc-1.md"]
