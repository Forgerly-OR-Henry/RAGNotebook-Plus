from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage

from agent.prompts.loader import load_prompt
from core.background_init import init_manager
from core.logger_handler import logger


def extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


async def generate_auto_tags(content: str) -> dict:
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
