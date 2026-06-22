from pathlib import Path

from agent.prompts.registry import PROMPT_FILES
from core.logger_handler import logger


def load_prompt(prompt_type: str = 'main_prompt'):
    """
    加载指定类型的提示词模板

    Args:
        prompt_type: 提示词类型，对应 agent.prompts.registry.PROMPT_FILES 中的键名
            - main_prompt: 主要提示词
            - rag_summary_prompt: RAG摘要提示词
            - report_prompt: 报告提示词
            - reorder_prompt: 文档重排序提示词

    Returns:
        提示词模板内容
    """
    try:
        if prompt_type not in PROMPT_FILES:
            logger.error(f"【加载提示词模板】配置中不存在 {prompt_type} 类型的提示词")
            raise KeyError(f"配置中不存在 {prompt_type} 类型的提示词")

        prompt_path = Path(__file__).resolve().parent / PROMPT_FILES[prompt_type]
    except Exception as e:
        logger.error(f"【加载提示词模板】加载 {PROMPT_FILES.get(prompt_type, prompt_type)} 时出错: {e}")
        raise e

    try:
        return prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"【加载提示词模板】读取 {prompt_path} 时出错: {e}")
        raise e

if __name__ == '__main__':
    print(load_prompt('report_prompt'))
