"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

PROMPT_FILES = {
    "main_prompt": "main_prompt.txt",
    "rag_summary_prompt": "rag_summarize.txt",
    "report_prompt": "report_prompt.txt",
    "reorder_prompt": "reorder_prompt.txt",
    "auto_tag_prompt": "auto_tag_prompt.txt",
    "autocomplete_prompt": "autocomplete_prompt.txt",
    "write_assistant_prompt": "write_assistant_prompt.txt",
}
