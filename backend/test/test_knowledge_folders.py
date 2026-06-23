from starlette.routing import Match

from mvc.controllers.knowledge_controller import knowledge_router
from mvc.models.base import Base
from mvc.models.knowledge_document import KnowledgeDocument
from mvc.models.knowledge_folder import KnowledgeFolder, KnowledgeFolderAssignment
from mvc.schemas import (
    KnowledgeBatchCategoryRequest,
    KnowledgeBatchFolderRequest,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderUpdate,
)


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
    assert _matched_endpoint("/knowledge/stats", "GET") == "get_knowledge_stats"
    assert _matched_endpoint("/knowledge/category/work", "DELETE") == "delete_knowledge_category"
