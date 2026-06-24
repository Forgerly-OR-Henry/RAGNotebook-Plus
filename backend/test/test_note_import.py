"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
import io
from datetime import datetime, timedelta, timezone

import pytest

from mvc.models.document import Document
from mvc.models.note import Note
from mvc.models.storage_object import StorageObject
from mvc.schemas import NoteCreate
from mvc.services.note_index_service import NoteIndexService
from mvc.services.note_service import (
    NoteImportError,
    NoteService,
    _note_search_sort_key,
    _rank_note_search_match,
    build_imported_note_payload,
)


class BlockingVectorStore:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - started（实例属性，由构造函数注入或初始化）：保存started相关状态、配置或数据字段。
    - release（实例属性，由构造函数注入或初始化）：保存release相关状态、配置或数据字段。
    - finished（实例属性，由构造函数注入或初始化）：保存finished相关状态、配置或数据字段。
    """
    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = asyncio.Event()

    async def add_documents(self, documents, ids=None, user_id=None):
        """
        用途：异步执行add documents相关业务流程。

        参数：
        - documents（未显式标注）：调用方传入的documents数据或控制参数，用于驱动本函数处理流程。
        - ids（未显式标注）：调用方传入的ids数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        self.started.set()
        await self.release.wait()
        self.finished.set()
        return ids or []

    async def upsert_documents(self, **kwargs):
        """
        用途：异步执行upsert documents相关业务流程。

        参数：
        - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        self.started.set()
        await self.release.wait()
        self.finished.set()
        return [kwargs.get("source_id", "note")]


class DummySession:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - objects（实例属性，由构造函数注入或初始化）：保存objects相关状态、配置或数据字段。
    """
    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.objects = []

    def add(self, note):
        """
        用途：执行add相关业务逻辑。

        参数：
        - note（未显式标注）：调用方传入的note数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.objects.append(note)

    async def commit(self):
        """
        用途：异步执行commit相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return None

    async def refresh(self, note):
        """
        用途：异步执行refresh相关业务流程。

        参数：
        - note（未显式标注）：调用方传入的note数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return None


class DummyStorageService:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
    """
    async def upload_bytes(self, *, kind, user_id, object_id, filename, content, mime_type):
        """
        用途：上传upload bytes相关的数据或流程。

        参数：
        - kind（未显式标注）：调用方传入的kind数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - object_id（未显式标注）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。
        - filename（未显式标注）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - content（未显式标注）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
        - mime_type（未显式标注）：调用方传入的mime_type数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return StorageObject(
            id=object_id,
            backend="local",
            host="localhost",
            protocol=None,
            storage_uri=f"files://{kind}/{user_id}/{object_id}.md",
            storage_path=f"/tmp/{object_id}.md",
            original_filename=filename,
            mime_type=mime_type,
            file_ext=".md",
            checksum_sha256="hash",
            size_bytes=len(content),
            status="uploaded",
        )

    async def delete_storage_object_data(self, storage_object):
        """
        用途：删除delete storage object data相关的数据或流程。

        参数：
        - storage_object（未显式标注）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return None


def test_markdown_import_payload_preserves_markdown():
    """
    用途：执行test markdown import payload preserves markdown相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payload = build_imported_note_payload(
        "weekly-plan.md",
        "# 周计划\n\n- 阅读\n- 复盘".encode("utf-8"),
    )

    assert payload.title == "weekly-plan"
    assert payload.content == "# 周计划\n\n- 阅读\n- 复盘"


def test_text_import_payload_preserves_plain_text_and_uses_category():
    """
    用途：执行test text import payload preserves plain text and uses category相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payload = build_imported_note_payload(
        "plain.txt",
        "第一段<script>\n第二行\n\n第三段".encode("utf-8"),
        category="导入",
    )

    assert payload.title == "plain"
    assert payload.category == "导入"
    assert payload.content == "第一段&lt;script&gt;\n第二行\n\n第三段"


def test_docx_import_payload_keeps_common_document_structure():
    """
    用途：执行test docx import payload keeps common document structure相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("项目计划", level=1)
    document.add_paragraph("完成需求梳理", style="List Bullet")
    document.add_paragraph("输出初版方案", style="List Number")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "阶段"
    table.cell(0, 1).text = "状态"
    table.cell(1, 0).text = "导入"
    table.cell(1, 1).text = "完成"

    buf = io.BytesIO()
    document.save(buf)

    payload = build_imported_note_payload("plan.docx", buf.getvalue())

    assert payload.title == "项目计划"
    assert "# 项目计划" in payload.content
    assert "- 完成需求梳理" in payload.content
    assert "1. 输出初版方案" in payload.content
    assert "| 阶段 | 状态 |" in payload.content
    assert "| 导入 | 完成 |" in payload.content


def test_note_import_rejects_unsupported_extension():
    """
    用途：执行test note import rejects unsupported extension相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    with pytest.raises(NoteImportError, match="文件类型不支持"):
        build_imported_note_payload("archive.zip", b"content")


def test_create_note_returns_before_vector_write_finishes():
    """
    用途：执行test create note returns before vector write finishes相关业务逻辑。

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
        store = BlockingVectorStore()
        service = NoteService(embed_model=None, storage_service=DummyStorageService())
        service.index_service.repository = store

        note = await asyncio.wait_for(
            service.create_note(
                DummySession(),
                "user-1",
                NoteCreate(title="快速保存", content="保存不等待向量写入", category="测试"),
            ),
            timeout=0.2,
        )

        assert note.title == "快速保存"
        assert not store.finished.is_set()

        await asyncio.wait_for(store.started.wait(), timeout=1)
        store.release.set()
        await asyncio.wait_for(store.finished.wait(), timeout=1)

    asyncio.run(scenario())


def test_note_vector_background_task_times_out(monkeypatch):
    """
    用途：执行test note vector background task times out相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

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
        store = BlockingVectorStore()
        service = NoteService(embed_model=None, storage_service=DummyStorageService())
        service.index_service.repository = store
        monkeypatch.setenv("NOTE_INDEX_TIMEOUT_SECONDS", "0.01")

        await asyncio.wait_for(
            service._upsert_note_vector("note-1", "user-1", "标题", "会触发后台索引超时"),
            timeout=1,
        )

        assert store.started.is_set()
        assert not store.finished.is_set()

    asyncio.run(scenario())


def test_refresh_note_vector_keeps_existing_index_until_new_upsert_succeeds():
    """
    用途：执行test refresh note vector keeps existing index until new upsert succeeds相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    class RecordingRepository:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - calls（实例属性，由构造函数注入或初始化）：保存calls相关状态、配置或数据字段。
        """
        def __init__(self):
            """
            用途：执行init相关业务逻辑。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            self.calls = []

        async def delete_source(self, **kwargs):
            """
            用途：删除delete source相关的数据或流程。

            参数：
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            self.calls.append(("delete", kwargs))
            return 1

        async def upsert_documents(self, **kwargs):
            """
            用途：异步执行upsert documents相关业务流程。

            参数：
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            self.calls.append(("upsert", kwargs))
            return ["chunk-1"]

    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        repository = RecordingRepository()
        service = NoteIndexService(repository=repository)

        refreshed_count = await service.refresh_note("note-1", "user-1", "标题", "更新后的正文")
        cleared_count = await service.refresh_note("note-1", "user-1", "标题", "")

        assert refreshed_count == 1
        assert cleared_count == 0
        assert [call[0] for call in repository.calls] == ["upsert", "delete"]

    asyncio.run(scenario())


def test_delete_note_removes_visible_records_and_project_refs_when_index_cleanup_fails(monkeypatch):
    """
    用途：执行test delete note removes visible records and project refs when index cleanup fails相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    events = []

    class FailingIndexService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def delete_note(self, note_id, user_id):
            """
            用途：删除delete note相关的数据或流程。

            参数：
            - note_id（未显式标注）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            events.append(("index_delete", note_id))
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

    note = Note(
        id="note-1",
        user_id="user-1",
        document_id="doc-1",
        title="项目笔记",
    )
    document = Document(
        id="doc-1",
        user_id="user-1",
        source_type="note",
        title="项目笔记",
        storage_object_id="store-1",
        content_hash="hash",
        file_size=100,
        status="ready",
    )
    storage_object = StorageObject(
        id="store-1",
        backend="local",
        host="local",
        storage_uri="local://notes/user-1/store-1.md",
        storage_path="notes/user-1/store-1.md",
        original_filename="项目笔记.md",
        checksum_sha256="hash",
        size_bytes=100,
    )

    storage_service = FakeStorageService()
    service = NoteService(embed_model=None, storage_service=storage_service)
    service.index_service = FailingIndexService()

    async def fake_get_note_row(db, note_id, user_id):
        """
        用途：异步执行fake get note row相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - note_id（未显式标注）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return note, document, storage_object

    monkeypatch.setattr(service, "_get_note_row", fake_get_note_row)

    db = FakeDb()
    assert asyncio.run(service.delete_note(db, "note-1", "user-1")) is True
    assert db.committed is True
    assert db.deleted == []
    assert [statement.table.name for statement in db.executed] == [
        "note_folder_assignments",
        "project_sources",
        "notes",
        "documents",
        "storage_objects",
    ]
    assert events == [
        ("index_delete", "note-1"),
        ("execute", "note_folder_assignments"),
        ("execute", "project_sources"),
        ("execute", "notes"),
        ("execute", "documents"),
        ("execute", "storage_objects"),
        ("commit", None),
        ("storage_delete", "notes/user-1/store-1.md"),
    ]
    assert storage_service.deleted_paths == ["notes/user-1/store-1.md"]


def test_note_search_orders_exact_matches_before_fuzzy_matches():
    """
    用途：执行test note search orders exact matches before fuzzy matches相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    now = datetime.now(timezone.utc)
    exact = Note(
        id="exact",
        user_id="user-1",
        title="机器学习",
        document_id="exact",
        category="学习",
        is_pinned=False,
        updated_at=now - timedelta(days=3),
    )
    content_match = Note(
        id="content",
        user_id="user-1",
        title="课程记录",
        document_id="content",
        category="学习",
        is_pinned=True,
        updated_at=now,
    )
    fuzzy = Note(
        id="fuzzy",
        user_id="user-1",
        title="机器视觉学习路线",
        document_id="fuzzy",
        category="学习",
        is_pinned=True,
        updated_at=now + timedelta(days=1),
    )

    matches = [
        (_rank_note_search_match(content_match, "机器学习", "今天整理机器学习笔记"), content_match),
        (_rank_note_search_match(fuzzy, "机器学习", "较新的笔记"), fuzzy),
        (_rank_note_search_match(exact, "机器学习", "旧笔记"), exact),
    ]

    assert [rank for rank, _ in matches] == [4, 6, 0]
    assert [note.id for _, note in sorted(matches, key=_note_search_sort_key)] == ["exact", "content", "fuzzy"]
