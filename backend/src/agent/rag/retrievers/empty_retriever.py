"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


class EmptyRetriever(BaseRetriever):
    """始终返回空结果的检索器"""

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        """
        用途：异步执行aget relevant documents相关业务流程。

        参数：
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - run_manager（CallbackManagerForRetrieverRun | None）：调用方传入的run_manager数据或控制参数，用于驱动本函数处理流程。

        返回：list[Document]；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return []

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        """
        用途：读取或查询get relevant documents相关的数据或流程。

        参数：
        - query（str）：调用方传入的query数据或控制参数，用于驱动本函数处理流程。
        - run_manager（CallbackManagerForRetrieverRun | None）：调用方传入的run_manager数据或控制参数，用于驱动本函数处理流程。

        返回：list[Document]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return []
