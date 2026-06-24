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
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = asyncio.Event()

    async def add_documents(self, documents, ids=None, user_id=None):
        self.started.set()
        await self.release.wait()
        self.finished.set()
        return ids or []

    async def upsert_documents(self, **kwargs):
        self.started.set()
        await self.release.wait()
        self.finished.set()
        return [kwargs.get("source_id", "note")]


class DummySession:
    def __init__(self):
        self.objects = []

    def add(self, note):
        self.objects.append(note)

    async def commit(self):
        return None

    async def refresh(self, note):
        return None


class DummyStorageService:
    async def upload_bytes(self, *, kind, user_id, object_id, filename, content, mime_type):
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
        return None


def test_markdown_import_payload_preserves_markdown():
    payload = build_imported_note_payload(
        "weekly-plan.md",
        "# 周计划\n\n- 阅读\n- 复盘".encode("utf-8"),
    )

    assert payload.title == "weekly-plan"
    assert payload.content == "# 周计划\n\n- 阅读\n- 复盘"


def test_text_import_payload_preserves_plain_text_and_uses_category():
    payload = build_imported_note_payload(
        "plain.txt",
        "第一段<script>\n第二行\n\n第三段".encode("utf-8"),
        category="导入",
    )

    assert payload.title == "plain"
    assert payload.category == "导入"
    assert payload.content == "第一段&lt;script&gt;\n第二行\n\n第三段"


def test_docx_import_payload_keeps_common_document_structure():
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
    with pytest.raises(NoteImportError, match="文件类型不支持"):
        build_imported_note_payload("archive.zip", b"content")


def test_create_note_returns_before_vector_write_finishes():
    async def scenario():
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
    async def scenario():
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
    class RecordingRepository:
        def __init__(self):
            self.calls = []

        async def delete_source(self, **kwargs):
            self.calls.append(("delete", kwargs))
            return 1

        async def upsert_documents(self, **kwargs):
            self.calls.append(("upsert", kwargs))
            return ["chunk-1"]

    async def scenario():
        repository = RecordingRepository()
        service = NoteIndexService(repository=repository)

        refreshed_count = await service.refresh_note("note-1", "user-1", "标题", "更新后的正文")
        cleared_count = await service.refresh_note("note-1", "user-1", "标题", "")

        assert refreshed_count == 1
        assert cleared_count == 0
        assert [call[0] for call in repository.calls] == ["upsert", "delete"]

    asyncio.run(scenario())


def test_delete_note_removes_visible_records_and_project_refs_when_index_cleanup_fails(monkeypatch):
    events = []

    class FailingIndexService:
        async def delete_note(self, note_id, user_id):
            events.append(("index_delete", note_id))
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
