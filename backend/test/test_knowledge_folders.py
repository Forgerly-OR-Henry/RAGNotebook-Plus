"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio

import pytest
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
from mvc.services.knowledge_service import KnowledgeDocumentFileMissing, KnowledgeService


def _matched_endpoint(path: str, method: str) -> str:
    """
    用途：执行matched endpoint相关业务逻辑。

    参数：
    - path（str）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
    - method（str）：调用方传入的method数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test knowledge folder schema contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test knowledge folder request contracts相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test knowledge folder routes contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test delete document removes visible records when index cleanup fails相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    events = []

    class FailingIndexRepository:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def delete_source(self, **kwargs):
            """
            用途：删除delete source相关的数据或流程。

            参数：
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            raise RuntimeError("index unavailable")

    class FakeStorageService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - deleted_paths（实例属性，由构造函数注入或初始化）：保存deleted_paths相关状态、配置或数据字段。
        """
        def __init__(self):
            """
            用途：执行init相关业务逻辑。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            self.deleted_paths = []

        async def delete_storage_object_data(self, storage_object):
            """
            用途：删除delete storage object data相关的数据或流程。

            参数：
            - storage_object（未显式标注）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            events.append(("storage_delete", storage_object.storage_path))
            self.deleted_paths.append(storage_object.storage_path)

    class FakeDb:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - executed（实例属性，由构造函数注入或初始化）：保存executed相关状态、配置或数据字段。
        - deleted（实例属性，由构造函数注入或初始化）：保存deleted相关状态、配置或数据字段。
        - committed（实例属性，由构造函数注入或初始化）：保存committed相关状态、配置或数据字段。
        """
        def __init__(self):
            """
            用途：执行init相关业务逻辑。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            self.executed = []
            self.deleted = []
            self.committed = False

        async def execute(self, statement):
            """
            用途：异步执行execute相关业务流程。

            参数：
            - statement（未显式标注）：调用方传入的statement数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            events.append(("execute", statement.table.name))
            self.executed.append(statement)

        async def delete(self, item):
            """
            用途：异步执行delete相关业务流程。

            参数：
            - item（未显式标注）：调用方传入的item数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            self.deleted.append(item)

        async def commit(self):
            """
            用途：异步执行commit相关业务流程。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
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
        """
        用途：异步执行fake get document row相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（未显式标注）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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


def test_preview_reports_missing_stored_file(monkeypatch):
    """
    用途：执行test preview reports missing stored file相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    class MissingStorageService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def read_object_bytes(self, storage_object):
            """
            用途：异步执行read object bytes相关业务流程。

            参数：
            - storage_object（未显式标注）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            raise FileNotFoundError(storage_object.storage_path)

    document = Document(
        id="doc-1",
        user_id="user-1",
        source_type="knowledge",
        title="missing.pdf",
        storage_object_id="doc-1",
        content_hash="hash",
        file_size=100,
        file_ext=".pdf",
        mime_type="application/pdf",
        status="ready",
    )
    storage_object = StorageObject(
        id="doc-1",
        backend="local",
        host="local",
        storage_uri="local://knowledge/user-1/doc-1.pdf",
        storage_path="knowledge/user-1/doc-1.pdf",
        original_filename="missing.pdf",
        file_ext=".pdf",
        mime_type="application/pdf",
        checksum_sha256="hash",
        size_bytes=100,
    )
    knowledge_document = KnowledgeDocument(
        id="doc-1",
        user_id="user-1",
        document_id="doc-1",
        title="missing.pdf",
    )

    service = KnowledgeService(storage_service=MissingStorageService())

    async def fake_get_document_row(db, user_id, document_id):
        """
        用途：异步执行fake get document row相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - document_id（未显式标注）：调用方传入的document_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return document, storage_object, knowledge_document

    monkeypatch.setattr(service, "_get_document_row", fake_get_document_row)

    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        with pytest.raises(KnowledgeDocumentFileMissing, match="源文件已丢失"):
            await service.get_document_preview(None, "user-1", "doc-1")

    asyncio.run(scenario())
