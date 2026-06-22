import json

from langchain_core.messages import HumanMessage

from agent.prompts.loader import load_prompt
from core.background_init import init_manager
from core.logger_handler import logger


async def generate_review_question(content: str) -> dict:
    raw = ""
    try:
        prompt_template = load_prompt("review_question_prompt")
        prompt = prompt_template.format(content=content[:2000])
        response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        logger.debug(f"LLM 原始响应: {raw[:500]}")

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        brace_start = raw.find("{")
        if brace_start > 0:
            raw = raw[brace_start:]
        data = json.loads(raw)

        return {
            "question": data["question"],
            "choices": data["choices"],
            "answer": data["answer"],
        }
    except Exception as e:
        logger.error(f"生成回顾问题失败: {e} | raw={raw[:300]}")
        return {
            "question": "请回顾这篇笔记的主要内容",
            "choices": ["不太确定", "需要复习", "基本掌握", "完全理解"],
            "answer": "基本掌握",
        }
