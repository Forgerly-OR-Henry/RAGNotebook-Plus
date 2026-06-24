"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

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
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - source_type（实例属性，由构造函数注入或初始化）：保存source_type相关状态、配置或数据字段。
    """
    def __init__(self, source_type: str):
        """
        用途：执行init相关业务逻辑。

        参数：
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.source_type = source_type

    async def collect(self, db, user_id: str, source_ids: list[str], max_chunks: int):
        """
        用途：异步执行collect相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str]）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - max_chunks（int）：调用方传入的max_chunks数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行search相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
        - source_ids（list[str] | None）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
    """
    用途：执行test current schema declares document and index tables相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test current schema rejects legacy tables相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    unsupported = db_config._unsupported_schema_tables({"notes", "user_service", "legacy_version"})

    assert unsupported == {"user_service", "legacy_version"}


def test_source_registry_collects_mixed_sources():
    """
    用途：执行test source registry collects mixed sources相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        registry = SourceRegistry([FakeProvider("note"), FakeProvider("knowledge")])

        chunks = await registry.collect(None, "user-1", "mixed", ["note-1", "knowledge-1"], max_chunks=4)

        assert [chunk.source_type for chunk in chunks] == ["note", "knowledge"]

    asyncio.run(scenario())


def test_source_registry_search_orders_by_score():
    """
    用途：执行test source registry search orders by score相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        registry = SourceRegistry([FakeProvider("knowledge"), FakeProvider("note")])

        chunks = await registry.search(None, "user-1", "query", source_type="mixed", top_k=2)

        assert [chunk.source_type for chunk in chunks] == ["note", "knowledge"]

    asyncio.run(scenario())


def test_rag_service_no_longer_reads_note_service_internal_store():
    """
    用途：执行test rag service no longer reads note service internal store相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    source = inspect.getsource(RagService)

    assert "." + "notes_store" not in source
    assert "Vector" + "StoreService(" not in source


def test_knowledge_router_uses_document_id_resources():
    """
    用途：执行test knowledge router uses document id resources相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
