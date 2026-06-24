"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import datetime
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass

from langchain_core.tools import tool

from utils.auth_utils import decode_django_jwt


@dataclass
class AgentToolCallbacks:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - rag_summary（Callable[[str, str | None, Callable | None], Awaitable[str]] | None）：保存rag_summary相关状态、配置或数据字段。
    - search_notes（Callable[[str, int, str], Awaitable[str]] | None）：保存search_notes相关状态、配置或数据字段。
    - note_stats（Callable[[str], Awaitable[str]] | None）：保存note_stats相关状态、配置或数据字段。
    - create_note（Callable[[str, str, str], Awaitable[str]] | None）：保存create_note相关状态、配置或数据字段。
    - related_notes（Callable[[str, int, str], Awaitable[str]] | None）：保存related_notes相关状态、配置或数据字段。
    """
    rag_summary: Callable[[str, str | None, Callable | None], Awaitable[str]] | None = None
    search_notes: Callable[[str, int, str], Awaitable[str]] | None = None
    note_stats: Callable[[str], Awaitable[str]] | None = None
    create_note: Callable[[str, str, str], Awaitable[str]] | None = None
    related_notes: Callable[[str, int, str], Awaitable[str]] | None = None


current_user_id_var: ContextVar[str | None] = ContextVar("current_user_id", default=None)
thinking_callback_var: ContextVar[Callable | None] = ContextVar("thinking_callback", default=None)
tool_callbacks_var: ContextVar[AgentToolCallbacks | None] = ContextVar("tool_callbacks", default=None)


def set_current_user_id(user_id: str):
    """设置当前用户ID到上下文"""
    current_user_id_var.set(user_id)


def get_current_user_id_from_context() -> str | None:
    """从上下文获取当前用户ID"""
    return current_user_id_var.get()


def set_thinking_callback(callback):
    """设置思考过程回调到上下文"""
    thinking_callback_var.set(callback)


def get_thinking_callback_from_context():
    """从上下文获取思考过程回调"""
    return thinking_callback_var.get()


def set_agent_tool_callbacks(callbacks: AgentToolCallbacks | None):
    """注入由 MVC gateway 提供的工具回调。"""
    tool_callbacks_var.set(callbacks)


def get_agent_tool_callbacks() -> AgentToolCallbacks | None:
    """
    用途：读取或查询get agent tool callbacks相关的数据或流程。

    参数：无显式业务参数。

    返回：AgentToolCallbacks | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return tool_callbacks_var.get()


def _missing_tool() -> str:
    """
    用途：执行missing tool相关业务逻辑。

    参数：无显式业务参数。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return "当前工具后端未初始化，请稍后重试。"


@tool(description=(
    "用于从向量数据库里检索文档并生成摘要，返回包含文档列表和摘要的结果。"
    "返回格式为：'摘要: [摘要内容]\n\n检索到的文档列表:\n1. [文档1内容]\n2. [文档2内容]\n...'。"
    "注意：文档已经过自动重排序，无需再调用重排序工具"
))
async def rag_summary_tools(query: str, user_id: str = None) -> str:
    """RAG 摘要工具"""
    effective_user_id = user_id or get_current_user_id_from_context()
    if not effective_user_id:
        return "错误: 无法确定用户身份，请提供有效的user_id"

    callbacks = get_agent_tool_callbacks()
    if callbacks is None or callbacks.rag_summary is None:
        return _missing_tool()
    return await callbacks.rag_summary(query, effective_user_id, get_thinking_callback_from_context())


@tool(description="当用户明确问自己的ID和用户名时，从JWT中获取当前用户ID和用户名，参数为完整的JWT token字符串")
async def get_user_info_tools(token: str) -> str:
    """获取用户信息工具"""
    payload = decode_django_jwt(token)
    if payload:
        user_id = payload.get("user_id", "未知")
        user_name = payload.get("user_name", "未知")
        return f"用户信息：\n- 用户ID: {user_id}\n- 用户名: {user_name}"
    return "无法解析JWT token，无法获取用户信息"


@tool(description="用于获取当前年月日时分的工具")
async def what_time_is_now() -> str:
    """获取当前年月日时分的工具"""
    return f"当前时间是：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"


@tool(description="语义搜索用户的笔记，根据关键词返回最相关的笔记列表。参数 query 为搜索关键词，top_k 为返回结果数量（默认5）。")
async def search_notes_tool(query: str, top_k: int = 5) -> str:
    """搜索笔记工具"""
    user_id = get_current_user_id_from_context()
    if not user_id:
        return "错误: 无法确定用户身份"
    callbacks = get_agent_tool_callbacks()
    if callbacks is None or callbacks.search_notes is None:
        return _missing_tool()
    return await callbacks.search_notes(query, top_k, user_id)


@tool(description="获取用户的笔记统计信息，包括笔记总数、各分类（工作/学习/生活/项目）的笔记数量。")
async def get_note_stats_tool() -> str:
    """笔记统计工具"""
    user_id = get_current_user_id_from_context()
    if not user_id:
        return "错误: 无法确定用户身份"
    callbacks = get_agent_tool_callbacks()
    if callbacks is None or callbacks.note_stats is None:
        return _missing_tool()
    return await callbacks.note_stats(user_id)


@tool(description=(
    "创建一篇新笔记。参数 title 为笔记标题，content 为笔记内容"
    "（支持Markdown格式，可选，不传则只创建标题）。"
    "创建后会自动生成向量索引和智能标签。"
))
async def create_note_tool(title: str, content: str = "") -> str:
    """创建笔记工具"""
    user_id = get_current_user_id_from_context()
    if not user_id:
        return "错误: 无法确定用户身份"
    callbacks = get_agent_tool_callbacks()
    if callbacks is None or callbacks.create_note is None:
        return _missing_tool()
    return await callbacks.create_note(title, content, user_id)


@tool(description="获取某篇笔记的关联推荐，包括语义相似的笔记和知识库文档。参数 note_id 为笔记ID，top_k 为返回数量（默认3）。")
async def get_related_notes_tool(note_id: str, top_k: int = 3) -> str:
    """关联笔记推荐工具"""
    user_id = get_current_user_id_from_context()
    if not user_id:
        return "错误: 无法确定用户身份"
    callbacks = get_agent_tool_callbacks()
    if callbacks is None or callbacks.related_notes is None:
        return _missing_tool()
    return await callbacks.related_notes(note_id, top_k, user_id)
