import asyncio
import json
from types import SimpleNamespace

from agent.indexing.index_repository import IndexRepository, clear_query_embedding_cache
from mvc.agent_gateway import chat_gateway
from mvc.models.base import Base
from mvc.models.chat_history import ChatSession
from mvc.models.project import ChatProject, ProjectSource
from mvc.schemas import ProjectCreateRequest, ProjectSourcesAddRequest, QueryRequest, SourceReference
from mvc.services.project_service import ProjectService
from mvc.services.sources.models import SourceChunk


def test_chat_projects_schema_contract():
    assert ChatProject.__tablename__ == "chat_projects"
    assert ProjectSource.__tablename__ == "project_sources"
    assert ChatSession.__table__.columns["project_id"].nullable
    assert "uq_project_source_ref" in {constraint.name for constraint in ProjectSource.__table__.constraints}
    assert {"chat_projects", "project_sources", "chat_sessions"} <= set(Base.metadata.tables)


def test_project_and_chat_request_schema_contract():
    project = ProjectCreateRequest(name="研究项目", description="论文资料")
    add_sources = ProjectSourcesAddRequest(
        sources=[
            SourceReference(source_type="note", source_id="note-1"),
            SourceReference(source_type="knowledge", source_id="doc-1"),
        ]
    )
    query = QueryRequest(
        query="总结 @论文",
        session_id="session-1",
        project_id="project-1",
        references=add_sources.sources,
    )

    assert project.name == "研究项目"
    assert query.project_id == "project-1"
    assert query.rag_enabled is True
    assert [ref.source_type for ref in query.references or []] == ["note", "knowledge"]

    direct_query = QueryRequest(query="你好", rag_enabled=False)
    assert direct_query.rag_enabled is False


def test_project_source_refs_are_deduped():
    refs = ProjectService._dedupe_refs(
        [
            SourceReference(source_type="note", source_id="note-1"),
            SourceReference(source_type="note", source_id="note-1"),
            SourceReference(source_type="knowledge", source_id="doc-1"),
        ]
    )

    assert [(ref.source_type, ref.source_id) for ref in refs] == [("note", "note-1"), ("knowledge", "doc-1")]


def test_scoped_rag_search_splits_mixed_source_refs(monkeypatch):
    class FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeRegistry:
        def __init__(self):
            self.calls = []

        async def search(self, db, user_id, query, source_type="mixed", top_k=6, source_ids=None):
            self.calls.append((user_id, query, source_type, tuple(source_ids or []), top_k))
            return [
                SourceChunk(
                    source_type=source_type,
                    source_id=(source_ids or [source_type])[0],
                    title=source_type,
                    content=query,
                    score=0.1 if source_type == "note" else 0.2,
                )
            ]

    registry = FakeRegistry()
    monkeypatch.setattr(chat_gateway, "AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr(chat_gateway, "get_source_registry", lambda: registry)

    refs = [
        SourceReference(source_type="note", source_id="note-1"),
        SourceReference(source_type="knowledge", source_id="doc-1"),
    ]
    chunks = asyncio.run(chat_gateway._search_sources("user-1", "query", "mixed", 4, source_refs=refs))

    assert [chunk.source_type for chunk in chunks] == ["note", "knowledge"]
    assert registry.calls == [
        ("user-1", "query", "note", ("note-1",), 4),
        ("user-1", "query", "knowledge", ("doc-1",), 4),
    ]


def test_project_default_sources_can_be_disabled():
    class FakeDb:
        execute_calls = 0

        async def get(self, model, id_):
            return SimpleNamespace(id=id_, user_id="user-1")

        async def execute(self, stmt):
            self.execute_calls += 1
            return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

    db = FakeDb()
    refs = asyncio.run(
        ProjectService().resolve_chat_references(
            db,
            "user-1",
            "project-1",
            references=None,
            use_default_sources=False,
        )
    )

    assert refs is None
    assert db.execute_calls == 0


def test_query_embedding_cache_reuses_same_model_query():
    class FakeEmbeddingModel:
        def __init__(self):
            self.calls = 0

        def embed_query(self, query):
            self.calls += 1
            return [1.0, 0.0, 0.5]

    clear_query_embedding_cache()
    model = FakeEmbeddingModel()
    first_repo = IndexRepository(embedding_model=model)
    second_repo = IndexRepository(embedding_model=model)

    first = asyncio.run(first_repo._embed_query("same query"))
    second = asyncio.run(second_repo._embed_query("same query"))

    assert first == second == [1.0, 0.0, 0.5]
    assert model.calls == 1


def _parse_sse_events(events: list[str]) -> list[dict]:
    payloads = []
    for event in events:
        data = event.strip().removeprefix("data: ")
        payloads.append(json.loads(data))
    return payloads


def test_stream_chat_bypasses_rag_when_disabled(monkeypatch):
    class FakeSessionManager:
        def __init__(self):
            self.persisted = None

        async def get_history(self, session_id, user_id, project_id=None):
            return [("之前的问题", "之前的回答")]

        async def add_message(self, *args, **kwargs):
            self.persisted = (args, kwargs)

    class ForbiddenRagService:
        def __init__(self, *args, **kwargs):
            raise AssertionError("RAG should not be used when rag_enabled is false")

    async def fake_stream(query, history=None, context_documents=None, rag_enabled=False):
        assert query == "你好"
        assert history == [("之前的问题", "之前的回答")]
        assert context_documents == []
        assert rag_enabled is False
        yield "你"
        yield "好"

    fake_session_manager = FakeSessionManager()
    monkeypatch.setattr(chat_gateway, "sm", SimpleNamespace(session_manager=fake_session_manager))
    monkeypatch.setattr(chat_gateway, "RagService", ForbiddenRagService)
    monkeypatch.setattr(chat_gateway, "stream_chat_model_response", fake_stream)

    async def scenario():
        return [
            event async for event in chat_gateway.stream_agent_response(
                "你好",
                "session-1",
                "user-1",
                rag_enabled=False,
            )
        ]

    payloads = _parse_sse_events(asyncio.run(scenario()))

    assert [payload["type"] for payload in payloads] == ["response", "response", "response", "done"]
    assert payloads[1]["content"] == "你"
    assert payloads[2]["content"] == "好"
    assert fake_session_manager.persisted[0][2] == "你好"


def test_stream_chat_uses_fast_rag_context_and_streams_model_chunks(monkeypatch):
    class FakeSessionManager:
        async def get_history(self, session_id, user_id, project_id=None):
            return []

        async def add_message(self, *args, **kwargs):
            pass

    class FakeRagService:
        def __init__(self, user_id, thinking_callback=None, source_search=None):
            self.user_id = user_id
            self.thinking_callback = thinking_callback

        async def get_reordered_documents(self, query, max_documents=3, use_hyde=False):
            assert query == "总结资料"
            assert max_documents == 3
            assert use_hyde is False
            if self.thinking_callback:
                await self.thinking_callback({"type": "thinking", "stage": "retrieval", "content": "检索中"})
            return ["[来源：知识库《A》]\n内容"]

    async def fake_stream(query, history=None, context_documents=None, rag_enabled=False):
        assert context_documents == ["[来源：知识库《A》]\n内容"]
        assert rag_enabled is True
        yield "答案"

    monkeypatch.setattr(chat_gateway, "sm", SimpleNamespace(session_manager=FakeSessionManager()))
    monkeypatch.setattr(chat_gateway, "RagService", FakeRagService)
    monkeypatch.setattr(chat_gateway, "stream_chat_model_response", fake_stream)

    async def scenario():
        return [
            event async for event in chat_gateway.stream_agent_response(
                "总结资料",
                "session-1",
                "user-1",
                rag_enabled=True,
            )
        ]

    payloads = _parse_sse_events(asyncio.run(scenario()))

    assert any(payload["type"] == "thinking" and payload["content"] == "检索中" for payload in payloads)
    assert any(payload["type"] == "response" and payload["content"] == "答案" for payload in payloads)
