"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

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
    """
    用途：执行test chat projects schema contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert ChatProject.__tablename__ == "chat_projects"
    assert ProjectSource.__tablename__ == "project_sources"
    assert ChatSession.__table__.columns["project_id"].nullable
    assert "uq_project_source_ref" in {constraint.name for constraint in ProjectSource.__table__.constraints}
    assert {"chat_projects", "project_sources", "chat_sessions"} <= set(Base.metadata.tables)


def test_project_and_chat_request_schema_contract():
    """
    用途：执行test project and chat request schema contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test project source refs are deduped相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    refs = ProjectService._dedupe_refs(
        [
            SourceReference(source_type="note", source_id="note-1"),
            SourceReference(source_type="note", source_id="note-1"),
            SourceReference(source_type="knowledge", source_id="doc-1"),
        ]
    )

    assert [(ref.source_type, ref.source_id) for ref in refs] == [("note", "note-1"), ("knowledge", "doc-1")]


def test_scoped_rag_search_splits_mixed_source_refs(monkeypatch):
    """
    用途：执行test scoped rag search splits mixed source refs相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    class FakeSession:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def __aenter__(self):
            """
            用途：异步执行aenter相关业务流程。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            """
            用途：异步执行aexit相关业务流程。

            参数：
            - exc_type（未显式标注）：调用方传入的exc_type数据或控制参数，用于驱动本函数处理流程。
            - exc（未显式标注）：调用方传入的exc数据或控制参数，用于驱动本函数处理流程。
            - tb（未显式标注）：调用方传入的tb数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return False

    class FakeRegistry:
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

        async def search(self, db, user_id, query, source_type="mixed", top_k=6, source_ids=None):
            """
            用途：异步执行search相关业务流程。

            参数：
            - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
            - query（未显式标注）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
            - source_type（未显式标注）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
            - top_k（未显式标注）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
            - source_ids（未显式标注）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
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
    """
    用途：执行test project default sources can be disabled相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    class FakeDb:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - execute_calls（类属性或 ORM 字段）：保存execute_calls相关状态、配置或数据字段。
        """
        execute_calls = 0

        async def get(self, model, id_):
            """
            用途：异步执行get相关业务流程。

            参数：
            - model（未显式标注）：调用方传入的model数据或控制参数，用于驱动本函数处理流程。
            - id_（未显式标注）：调用方传入的id_数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return SimpleNamespace(id=id_, user_id="user-1")

        async def execute(self, stmt):
            """
            用途：异步执行execute相关业务流程。

            参数：
            - stmt（未显式标注）：调用方传入的stmt数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
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
    """
    用途：执行test query embedding cache reuses same model query相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    class FakeEmbeddingModel:
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
            self.calls = 0

        def embed_query(self, query):
            """
            用途：执行embed query相关业务逻辑。

            参数：
            - query（未显式标注）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
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
    """
    用途：解析parse sse events相关的数据或流程。

    参数：
    - events（list[str]）：调用方传入的events数据或控制参数，用于驱动本函数处理流程。

    返回：list[dict]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payloads = []
    for event in events:
        data = event.strip().removeprefix("data: ")
        payloads.append(json.loads(data))
    return payloads


def test_stream_chat_bypasses_rag_when_disabled(monkeypatch):
    """
    用途：执行test stream chat bypasses rag when disabled相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    class FakeSessionManager:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - persisted（实例属性，由构造函数注入或初始化）：保存persisted相关状态、配置或数据字段。
        """
        def __init__(self):
            """
            用途：执行init相关业务逻辑。

            参数：无显式业务参数。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            self.persisted = None

        async def get_history(self, session_id, user_id, project_id=None):
            """
            用途：读取或查询get history相关的数据或流程。

            参数：
            - session_id（未显式标注）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
            - project_id（未显式标注）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return [("之前的问题", "之前的回答")]

        async def add_message(self, *args, **kwargs):
            """
            用途：异步执行add message相关业务流程。

            参数：
            - args（未显式标注）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            self.persisted = (args, kwargs)

    class ForbiddenRagService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        def __init__(self, *args, **kwargs):
            """
            用途：执行init相关业务逻辑。

            参数：
            - args（未显式标注）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            raise AssertionError("RAG should not be used when rag_enabled is false")

    async def fake_stream(query, history=None, context_documents=None, rag_enabled=False):
        """
        用途：异步执行fake stream相关业务流程。

        参数：
        - query（未显式标注）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - history（未显式标注）：调用方传入的history数据或控制参数，用于驱动本函数处理流程。
        - context_documents（未显式标注）：调用方传入的context_documents数据或控制参数，用于驱动本函数处理流程。
        - rag_enabled（未显式标注）：调用方传入的rag_enabled数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
    """
    用途：执行test stream chat uses fast rag context and streams model chunks相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    class FakeSessionManager:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def get_history(self, session_id, user_id, project_id=None):
            """
            用途：读取或查询get history相关的数据或流程。

            参数：
            - session_id（未显式标注）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
            - project_id（未显式标注）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return []

        async def add_message(self, *args, **kwargs):
            """
            用途：异步执行add message相关业务流程。

            参数：
            - args（未显式标注）：调用方传入的args数据或控制参数，用于驱动本函数处理流程。
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            pass

    class FakeRagService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：
        - user_id（实例属性，由构造函数注入或初始化）：保存user_id相关状态、配置或数据字段。
        - thinking_callback（实例属性，由构造函数注入或初始化）：保存thinking_callback相关状态、配置或数据字段。
        """
        def __init__(self, user_id, thinking_callback=None, source_search=None):
            """
            用途：执行init相关业务逻辑。

            参数：
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
            - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。
            - source_search（未显式标注）：调用方传入的source_search数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            self.user_id = user_id
            self.thinking_callback = thinking_callback

        async def get_reordered_documents(self, query, max_documents=3, use_hyde=False):
            """
            用途：读取或查询get reordered documents相关的数据或流程。

            参数：
            - query（未显式标注）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
            - max_documents（未显式标注）：调用方传入的max_documents数据或控制参数，用于驱动本函数处理流程。
            - use_hyde（未显式标注）：调用方传入的use_hyde数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            assert query == "总结资料"
            assert max_documents == 3
            assert use_hyde is False
            if self.thinking_callback:
                await self.thinking_callback({"type": "thinking", "stage": "retrieval", "content": "检索中"})
            return ["[来源：知识库《A》]\n内容"]

    async def fake_stream(query, history=None, context_documents=None, rag_enabled=False):
        """
        用途：异步执行fake stream相关业务流程。

        参数：
        - query（未显式标注）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - history（未显式标注）：调用方传入的history数据或控制参数，用于驱动本函数处理流程。
        - context_documents（未显式标注）：调用方传入的context_documents数据或控制参数，用于驱动本函数处理流程。
        - rag_enabled（未显式标注）：调用方传入的rag_enabled数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        assert context_documents == ["[来源：知识库《A》]\n内容"]
        assert rag_enabled is True
        yield "答案"

    monkeypatch.setattr(chat_gateway, "sm", SimpleNamespace(session_manager=FakeSessionManager()))
    monkeypatch.setattr(chat_gateway, "RagService", FakeRagService)
    monkeypatch.setattr(chat_gateway, "stream_chat_model_response", fake_stream)

    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
