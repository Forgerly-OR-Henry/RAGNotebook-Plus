"""
模块职责：AI 网关模块，负责把业务服务与模型、索引或 Agent 能力解耦。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
import json
import re

from langchain_core.messages import HumanMessage

from core.background_init import init_manager
from core.logger_handler import logger


def _extract_json(text: str) -> dict:
    """
    用途：执行extract json相关业务逻辑。

    参数：
    - text（str）：调用方传入的text数据或控制参数，用于驱动本函数处理流程。

    返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
    """
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


async def model_json(prompt: str) -> dict | None:
    """
    用途：异步执行model json相关业务流程。

    参数：
    - prompt（str）：调用方传入的prompt数据或控制参数，用于驱动本函数处理流程。

    返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    try:
        await asyncio.wait_for(init_manager.models_ready.wait(), timeout=20)
        response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
        return _extract_json(response.content.strip())
    except Exception as exc:
        logger.warning(f"快速测试 LLM JSON 生成失败，使用降级逻辑: {exc}")
        return None
