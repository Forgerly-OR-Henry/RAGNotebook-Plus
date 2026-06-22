import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from models.note import Note
from schemas import NoteCreate
from services.note_service import (
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
    def add(self, note):
        self.note = note

    async def commit(self):
        return None

    async def refresh(self, note):
        return None


def test_markdown_import_payload_converts_markdown_to_html():
    payload = build_imported_note_payload(
        "weekly-plan.md",
        "# 周计划\n\n- 阅读\n- 复盘".encode("utf-8"),
    )

    assert payload.title == "weekly-plan"
    assert "<h1>周计划</h1>" in payload.content
    assert "<li>阅读</li>" in payload.content


def test_text_import_payload_escapes_text_and_uses_category():
    payload = build_imported_note_payload(
        "plain.txt",
        "第一段<script>\n第二行\n\n第三段".encode("utf-8"),
        category="导入",
    )

    assert payload.title == "plain"
    assert payload.category == "导入"
    assert "&lt;script&gt;" in payload.content
    assert "第一段&lt;script&gt;<br>第二行" in payload.content
    assert "<p>第三段</p>" in payload.content


def test_note_import_rejects_unsupported_extension():
    with pytest.raises(NoteImportError, match="文件类型不支持"):
        build_imported_note_payload("archive.zip", b"content")


def test_create_note_returns_before_vector_write_finishes():
    async def scenario():
        store = BlockingVectorStore()
        service = NoteService(embed_model=None)
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
        content="旧笔记",
        category="学习",
        is_pinned=False,
        updated_at=now - timedelta(days=3),
    )
    content_match = Note(
        id="content",
        user_id="user-1",
        title="课程记录",
        content="今天整理机器学习笔记",
        category="学习",
        is_pinned=True,
        updated_at=now,
    )
    fuzzy = Note(
        id="fuzzy",
        user_id="user-1",
        title="机器视觉学习路线",
        content="较新的笔记",
        category="学习",
        is_pinned=True,
        updated_at=now + timedelta(days=1),
    )

    matches = [
        (_rank_note_search_match(content_match, "机器学习"), content_match),
        (_rank_note_search_match(fuzzy, "机器学习"), fuzzy),
        (_rank_note_search_match(exact, "机器学习"), exact),
    ]

    assert [rank for rank, _ in matches] == [4, 6, 0]
    assert [note.id for _, note in sorted(matches, key=_note_search_sort_key)] == ["exact", "content", "fuzzy"]
