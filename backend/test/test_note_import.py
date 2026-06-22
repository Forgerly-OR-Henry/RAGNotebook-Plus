import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from mvc.models.note import Note
from mvc.models.storage_object import StorageObject
from mvc.schemas import NoteCreate
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
    assert payload.content == "第一段<script>\n第二行\n\n第三段"


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
