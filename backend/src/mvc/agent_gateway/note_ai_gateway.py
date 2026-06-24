"""
模块职责：AI 网关模块，负责把业务服务与模型、索引或 Agent 能力解耦。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage

from agent.prompts.loader import load_prompt
from core.background_init import init_manager
from core.logger_handler import logger


def extract_json(text: str) -> str:
    """
    用途：执行extract json相关业务逻辑。

    参数：
    - text（str）：调用方传入的text数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


async def generate_auto_tags(content: str) -> dict:
    """
    用途：生成generate auto tags相关的数据或流程。

    参数：
    - content（str）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    prompt_template = load_prompt("auto_tag_prompt")
    prompt = prompt_template.replace("{content}", content)
    response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
    raw_output = response.content.strip()
    result = json.loads(extract_json(raw_output))
    return {
        "tags": result.get("tags", []),
        "category": result.get("category", "life"),
        "raw_output": raw_output,
    }


async def autocomplete(context: str) -> dict:
    """
    用途：异步执行autocomplete相关业务流程。

    参数：
    - context（str）：调用方传入的context数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    try:
        prompt_template = load_prompt("autocomplete_prompt")
        prompt = prompt_template.format(context=context[-200:])
        response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
        completion = response.content.strip()
        if completion and context.endswith(completion[:10]):
            completion = completion[10:]
        return {"success": True, "completion": completion}
    except Exception as e:
        logger.error(f"内联补全失败: {e}")
        return {"success": False, "completion": ""}


async def assist_stream(content: str, action: str) -> AsyncGenerator[str, None]:
    """
    用途：异步执行assist stream相关业务流程。

    参数：
    - content（str）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
    - action（str）：调用方传入的action数据或控制参数，用于驱动本函数处理流程。

    返回：AsyncGenerator[str, None]；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    chat_model = init_manager.chat_model
    prompt_template = load_prompt("write_assistant_prompt")
    prompt = prompt_template.format(content=content, action=action)

    try:
        async for chunk in chat_model.astream([HumanMessage(content=prompt)]):
            if chunk.content:
                yield f"data: {chunk.content}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"写作辅助流式输出失败: {e}")
        yield f"data: [ERROR: {str(e)}]\n\n"
