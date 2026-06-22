from __future__ import annotations

from collections.abc import AsyncGenerator

from agent.rag.rag_service import RagService
from agent.rag.reorder_service import reorder_service
from agent.runtime.agent import get_agent_response as runtime_get_agent_response
from agent.runtime.agent import get_agent_stream_response as runtime_get_agent_stream_response
from agent.runtime.agent_tools import AgentToolCallbacks
from core.background_init import init_manager
from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.schemas import NoteCreate
from mvc.services import session_manager as sm
from mvc.services.review_service import review_service
from mvc.services.sources.registry import get_source_registry


async def _search_sources(user_id: str, query: str, source_type: str, top_k: int) -> list:
    async with AsyncSessionLocal() as db:
        return await get_source_registry().search(db, user_id, query, source_type=source_type, top_k=top_k)


async def get_documents_and_summary(query: str, user_id: str, thinking_callback=None) -> dict:
    service = RagService(user_id, thinking_callback=thinking_callback, source_search=_search_sources)
    return await service.get_documents_and_summary(query)


async def rag_summary(query: str, user_id: str, thinking_callback=None) -> str:
    result = await get_documents_and_summary(query, user_id, thinking_callback=thinking_callback)
    return result.get("summary", "抱歉，处理您的请求时出现了错误。")


async def rag_summary_tool_result(query: str, user_id: str | None, thinking_callback=None) -> str:
    if not user_id:
        return "错误: 无法确定用户身份，请提供有效的user_id"

    result = await get_documents_and_summary(query, user_id, thinking_callback=thinking_callback)
    documents = result.get("documents", [])
    summary = result.get("summary", "")

    formatted_result = f"摘要: {summary}\n\n"
    formatted_result += "检索到的文档列表（已重排序）:\n"
    for i, doc in enumerate(documents, 1):
        formatted_result += f"{i}. {doc}\n"
    return formatted_result


async def reorder_documents(query: str, documents: list[str]) -> dict:
    return await reorder_service.reorder_documents(query, documents)


async def _search_notes_callback(query: str, top_k: int, user_id: str) -> str:
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


async def _today_reviews_callback(user_id: str) -> str:
    async with AsyncSessionLocal() as db:
        try:
            reviews = await review_service.get_today_reviews(db, user_id)
            if not reviews:
                return "今日没有待回顾的笔记，继续保持！"
            lines = [f"📅 今日待回顾笔记（共 {len(reviews)} 篇）\n"]
            for i, rv in enumerate(reviews, 1):
                lines.append(f"{i}. **{rv['title']}**")
                lines.append(f"   回顾次数: 第 {rv['review_count'] + 1} 次")
                lines.append(f"   内容预览: {rv['content_preview'][:100]}...\n")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"获取今日回顾失败: {e}")
            return f"获取今日回顾时出错: {str(e)}"


async def _mark_reviewed_callback(note_id: str, user_id: str) -> str:
    async with AsyncSessionLocal() as db:
        try:
            result = await review_service.mark_reviewed(db, note_id, user_id)
            if result["success"]:
                return f"✅ 已标记回顾完成！第 {result['review_count']} 次回顾，下次回顾间隔 {result['interval_days']} 天。"
            return f"标记失败: {result['message']}"
        except Exception as e:
            logger.error(f"标记回顾失败: {e}")
            return f"标记回顾时出错: {str(e)}"


async def _create_note_callback(title: str, content: str, user_id: str) -> str:
    async with AsyncSessionLocal() as db:
        try:
            payload = NoteCreate(title=title, content=content)
            note = await init_manager.note_service.create_note(db, user_id, payload)
            return f"✅ 笔记创建成功！\n- 标题: {note.title}\n- ID: {note.id}\n- 标签和分类正在后台生成中..."
        except Exception as e:
            logger.error(f"创建笔记失败: {e}")
            return f"创建笔记时出错: {str(e)}"


async def _related_notes_callback(note_id: str, top_k: int, user_id: str) -> str:
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


def _build_tool_callbacks() -> AgentToolCallbacks:
    return AgentToolCallbacks(
        rag_summary=rag_summary_tool_result,
        search_notes=_search_notes_callback,
        note_stats=_note_stats_callback,
        today_reviews=_today_reviews_callback,
        mark_reviewed=_mark_reviewed_callback,
        create_note=_create_note_callback,
        related_notes=_related_notes_callback,
    )


async def get_agent_response(query: str, history: list[tuple] | None, user_id: str) -> dict:
    return await runtime_get_agent_response(
        query,
        history,
        user_id=user_id,
        tool_callbacks=_build_tool_callbacks(),
    )


async def stream_agent_response(query: str, session_id: str, user_id: str) -> AsyncGenerator[str, None]:
    history = await sm.session_manager.get_history(session_id, user_id)

    async def persist_message(user_query: str, response: str) -> None:
        await sm.session_manager.add_message(session_id, user_id, user_query, response)

    async for event in runtime_get_agent_stream_response(
        query,
        session_id,
        user_id,
        history=history,
        persist_message=persist_message,
        tool_callbacks=_build_tool_callbacks(),
    ):
        yield event
