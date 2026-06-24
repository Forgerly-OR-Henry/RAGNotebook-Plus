"""
模块职责：AI 网关模块，负责把业务服务与模型、索引或 Agent 能力解耦。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from agent.rag.rag_service import RagService
from agent.rag.reorder_service import reorder_service
from agent.runtime.agent import get_agent_response as runtime_get_agent_response
from agent.runtime.agent import stream_chat_model_response
from agent.runtime.agent_tools import AgentToolCallbacks
from core.background_init import init_manager
from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.schemas import NoteCreate
from mvc.schemas.sources import SourceReference
from mvc.services import session_manager as sm
from mvc.services.sources.registry import get_source_registry


def _source_ref_dict(ref: SourceReference) -> dict:
    """
    用途：执行source ref dict相关业务逻辑。

    参数：
    - ref（SourceReference）：调用方传入的ref数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return {"source_type": ref.source_type, "source_id": ref.source_id}


async def _search_sources(
    user_id: str,
    query: str,
    source_type: str,
    top_k: int,
    source_refs: list[SourceReference] | None = None,
) -> list:
    """
    用途：搜索search sources相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
    - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。

    返回：list；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        registry = get_source_registry()
        if source_refs is None:
            return await registry.search(db, user_id, query, source_type=source_type, top_k=top_k)

        refs_by_type: dict[str, list[str]] = {"note": [], "knowledge": []}
        for ref in source_refs:
            refs_by_type.setdefault(ref.source_type, []).append(ref.source_id)

        if source_type == "mixed":
            chunks = []
            for scoped_type, source_ids in refs_by_type.items():
                if not source_ids:
                    continue
                chunks.extend(
                    await registry.search(
                        db,
                        user_id,
                        query,
                        source_type=scoped_type,
                        top_k=top_k,
                        source_ids=source_ids,
                    )
                )
            chunks.sort(key=lambda chunk: chunk.score if chunk.score is not None else 999999.0)
            return chunks[:top_k]

        scoped_ids = refs_by_type.get(source_type, [])
        if not scoped_ids:
            return []
        return await registry.search(db, user_id, query, source_type=source_type, top_k=top_k, source_ids=scoped_ids)


def _build_source_search(source_refs: list[SourceReference] | None = None):
    """
    用途：构建build source search相关的数据或流程。

    参数：
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async def search(user_id: str, query: str, source_type: str, top_k: int) -> list:
        """
        用途：异步执行search相关业务流程。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - source_type（str）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。

        返回：list；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await _search_sources(user_id, query, source_type, top_k, source_refs=source_refs)

    return search


async def get_documents_and_summary(
    query: str,
    user_id: str,
    thinking_callback=None,
    source_refs: list[SourceReference] | None = None,
) -> dict:
    """
    用途：读取或查询get documents and summary相关的数据或流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    service = RagService(user_id, thinking_callback=thinking_callback, source_search=_build_source_search(source_refs))
    return await service.get_documents_and_summary(query)


async def rag_summary(query: str, user_id: str, thinking_callback=None) -> str:
    """
    用途：异步执行rag summary相关业务流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    result = await get_documents_and_summary(query, user_id, thinking_callback=thinking_callback)
    return result.get("summary", "抱歉，处理您的请求时出现了错误。")


async def rag_summary_tool_result(
    query: str,
    user_id: str | None,
    thinking_callback=None,
    source_refs: list[SourceReference] | None = None,
) -> str:
    """
    用途：异步执行rag summary tool result相关业务流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - user_id（str | None）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    if not user_id:
        return "错误: 无法确定用户身份，请提供有效的user_id"

    result = await get_documents_and_summary(query, user_id, thinking_callback=thinking_callback, source_refs=source_refs)
    documents = result.get("documents", [])
    summary = result.get("summary", "")

    formatted_result = f"摘要: {summary}\n\n"
    formatted_result += "检索到的文档列表（已重排序）:\n"
    for i, doc in enumerate(documents, 1):
        formatted_result += f"{i}. {doc}\n"
    return formatted_result


async def reorder_documents(query: str, documents: list[str]) -> dict:
    """
    用途：异步执行reorder documents相关业务流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - documents（list[str]）：调用方传入的documents数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await reorder_service.reorder_documents(query, documents)


async def _search_notes_callback(query: str, top_k: int, user_id: str) -> str:
    """
    用途：搜索search notes callback相关的数据或流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        try:
            results = await init_manager.note_service.search_notes(db, user_id, query, top_k=top_k)
            if not results:
                return "未找到相关笔记"
            lines = [f"找到 {len(results)} 篇相关笔记：\n"]
            for i, note in enumerate(results, 1):
                lines.append(f"{i}. **{note.title}**")
                if note.category:
                    lines.append(f"   分类: {note.category}")
                if note.tags:
                    lines.append(f"   标签: {', '.join(note.tags)}")
                lines.append(f"   内容预览: {note.content[:200]}...\n")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"搜索笔记失败: {e}")
            return f"搜索笔记时出错: {str(e)}"


async def _note_stats_callback(user_id: str) -> str:
    """
    用途：异步执行note stats callback相关业务流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        try:
            stats = await init_manager.note_service.get_category_stats(db, user_id)
            lines = ["📊 笔记统计\n"]
            lines.append(f"总笔记数: {stats['total']}\n")
            lines.append("各分类:")
            for cat in stats["categories"]:
                emoji = {"work": "💼", "study": "📖", "life": "🏠", "project": "🚀"}.get(cat["category"], "📄")
                lines.append(f"  {emoji} {cat['category']}: {cat['count']} 篇")
            if stats["uncategorized"] > 0:
                lines.append(f"  📄 未分类: {stats['uncategorized']} 篇")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"获取笔记统计失败: {e}")
            return f"获取笔记统计时出错: {str(e)}"


async def _create_note_callback(title: str, content: str, user_id: str) -> str:
    """
    用途：创建create note callback相关的数据或流程。

    参数：
    - title（str）：调用方传入的title数据或控制参数，用于驱动本函数处理流程。
    - content（str）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        try:
            payload = NoteCreate(title=title, content=content)
            note = await init_manager.note_service.create_note(db, user_id, payload)
            return f"✅ 笔记创建成功！\n- 标题: {note.title}\n- ID: {note.id}\n- 标签和分类正在后台生成中..."
        except Exception as e:
            logger.error(f"创建笔记失败: {e}")
            return f"创建笔记时出错: {str(e)}"


async def _related_notes_callback(note_id: str, top_k: int, user_id: str) -> str:
    """
    用途：异步执行related notes callback相关业务流程。

    参数：
    - note_id（str）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
    - top_k（int）：调用方传入的top_k数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as db:
        try:
            related = await init_manager.note_service.get_related_notes(db, note_id, user_id, top_k=top_k)
            if not related:
                return "未找到关联笔记或知识库文档"
            lines = [f"🔗 关联推荐（共 {len(related)} 项）\n"]
            for i, item in enumerate(related, 1):
                source_label = "📝 笔记" if item["source"] == "note" else "📚 知识库"
                lines.append(f"{i}. {source_label} — {item['title']}")
                lines.append(f"   相似度: {item['similarity']}")
                lines.append(f"   预览: {item['content_preview'][:100]}...\n")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"获取关联推荐失败: {e}")
            return f"获取关联推荐时出错: {str(e)}"


def _build_tool_callbacks(source_refs: list[SourceReference] | None = None) -> AgentToolCallbacks:
    """
    用途：构建build tool callbacks相关的数据或流程。

    参数：
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。

    返回：AgentToolCallbacks；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async def scoped_rag_summary(query: str, user_id: str | None, thinking_callback=None) -> str:
        """
        用途：异步执行scoped rag summary相关业务流程。

        参数：
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - user_id（str | None）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await rag_summary_tool_result(query, user_id, thinking_callback=thinking_callback, source_refs=source_refs)

    return AgentToolCallbacks(
        rag_summary=scoped_rag_summary,
        search_notes=_search_notes_callback,
        note_stats=_note_stats_callback,
        create_note=_create_note_callback,
        related_notes=_related_notes_callback,
    )


async def get_agent_response(query: str, history: list[tuple] | None, user_id: str) -> dict:
    """
    用途：读取或查询get agent response相关的数据或流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - history（list[tuple] | None）：调用方传入的history数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return await runtime_get_agent_response(
        query,
        history,
        user_id=user_id,
        tool_callbacks=_build_tool_callbacks(),
    )


async def stream_agent_response(
    query: str,
    session_id: str,
    user_id: str,
    project_id: str | None = None,
    source_refs: list[SourceReference] | None = None,
    rag_enabled: bool = True,
) -> AsyncGenerator[str, None]:
    """
    用途：流式处理stream agent response相关的数据或流程。

    参数：
    - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
    - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - project_id（str | None）：调用方传入的project_id数据或控制参数，用于驱动本函数处理流程。
    - source_refs（list[SourceReference] | None）：调用方传入的source_refs数据或控制参数，用于驱动本函数处理流程。
    - rag_enabled（bool）：调用方传入的rag_enabled数据或控制参数，用于驱动本函数处理流程。

    返回：AsyncGenerator[str, None]；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    history = await sm.session_manager.get_history(session_id, user_id, project_id=project_id)

    async def persist_message(user_query: str, response: str) -> None:
        """
        用途：异步执行persist message相关业务流程。

        参数：
        - user_query（str）：调用方传入的user_query数据或控制参数，用于驱动本函数处理流程。
        - response（str）：调用方传入的response数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        reference_payload = [_source_ref_dict(ref) for ref in source_refs] if source_refs else None
        await sm.session_manager.add_message(
            session_id,
            user_id,
            user_query,
            response,
            project_id=project_id,
            references=reference_payload,
        )

    def sse(payload: dict) -> str:
        """
        用途：执行sse相关业务逻辑。

        参数：
        - payload（dict）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    thinking_queue: asyncio.Queue[dict] = asyncio.Queue()

    async def thinking_callback(data: dict) -> None:
        """
        用途：异步执行thinking callback相关业务流程。

        参数：
        - data（dict）：调用方传入的data数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        logger.info(f"【思考过程】{data.get('stage', 'unknown')}: {data.get('content', '')}")
        await thinking_queue.put(data)

    async def drain_thinking_queue() -> list[str]:
        """
        用途：异步执行drain thinking queue相关业务流程。

        参数：无显式业务参数。

        返回：list[str]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        events = []
        while not thinking_queue.empty():
            try:
                event = thinking_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            events.append(sse(event))
            thinking_queue.task_done()
        return events

    try:
        logger.info(f"【AI问答流式响应】开始处理请求，用户ID: {user_id}, 会话ID: {session_id}, RAG: {rag_enabled}, 查询: {query}")
        yield sse({"type": "response", "content": "", "session_id": session_id})

        context_documents: list[str] = []
        if rag_enabled:
            service = RagService(user_id, thinking_callback=thinking_callback, source_search=_build_source_search(source_refs))
            retrieval_task = asyncio.create_task(service.get_reordered_documents(query, max_documents=3, use_hyde=False))
            while not retrieval_task.done():
                try:
                    event = await asyncio.wait_for(thinking_queue.get(), timeout=0.1)
                    yield sse(event)
                    thinking_queue.task_done()
                except asyncio.TimeoutError:
                    continue
            context_documents = await retrieval_task
            for event in await drain_thinking_queue():
                yield event

            if not context_documents:
                response = "抱歉，我没有找到相关资料。"
                await persist_message(query, response)
                yield sse({"type": "response", "content": response, "session_id": session_id})
                yield sse({"type": "done", "session_id": session_id})
                return

        response_parts: list[str] = []
        async for chunk in stream_chat_model_response(
            query,
            history=history,
            context_documents=context_documents,
            rag_enabled=rag_enabled,
        ):
            response_parts.append(chunk)
            yield sse({"type": "response", "content": chunk, "session_id": session_id})

        response = "".join(response_parts).strip() or "抱歉，我无法理解您的请求。"
        await persist_message(query, response)
        yield sse({"type": "done", "session_id": session_id})
        logger.info(f"【AI问答流式响应】处理完成，会话ID: {session_id}")
    except asyncio.CancelledError:
        logger.info(f"【AI问答流式响应】客户端断开，会话ID: {session_id}")
        raise
    except Exception as e:
        logger.error(f"【AI问答流式响应】处理请求失败: {e}", exc_info=True)
        yield sse({"type": "error", "content": f"错误: {str(e)}", "session_id": session_id})
        yield sse({"type": "done", "session_id": session_id})
