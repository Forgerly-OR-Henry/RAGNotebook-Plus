import asyncio
import json
import re

from langchain_core.messages import HumanMessage

from core.background_init import init_manager
from core.logger_handler import logger


def _extract_json(text: str) -> dict:
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
    try:
        await asyncio.wait_for(init_manager.models_ready.wait(), timeout=30)
        response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
        return _extract_json(response.content.strip())
    except Exception as exc:
        logger.warning(f"思维导图 LLM JSON 生成失败，使用降级逻辑: {exc}")
        return None
