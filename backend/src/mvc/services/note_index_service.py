"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from langchain_core.documents import Document

from mvc.agent_gateway.indexing_gateway import IndexRepository


class NoteIndexService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - repository（实例属性，由构造函数注入或初始化）：保存repository相关状态、配置或数据字段。
    """
    def __init__(self, repository: IndexRepository | None = None, embed_model=None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - repository（IndexRepository | None）：调用方传入的repository数据或控制参数，用于驱动本函数处理流程。
        - embed_model（未显式标注）：调用方传入的embed_model数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.repository = repository or IndexRepository(embedding_model=embed_model)

    async def upsert_note(self, note_id: str, user_id: str, title: str, content: str) -> int:
        """
        用途：异步执行upsert note相关业务流程。

        参数：
        - note_id（str）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - title（str）：调用方传入的title数据或控制参数，用于驱动本函数处理流程。
        - content（str）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not content.strip():
            return 0
        doc = Document(
            page_content=content,
            metadata={
                "note_id": note_id,
                "document_id": note_id,
                "title": title,
                "doc_type": "note",
            },
        )
        ids = await self.repository.upsert_documents(
            source_type="note",
            source_id=note_id,
            user_id=user_id,
            documents=[doc],
            metadata={"title": title, "note_id": note_id, "document_id": note_id},
        )
        return len(ids)

    async def refresh_note(self, note_id: str, user_id: str, title: str, content: str) -> int:
        """
        用途：异步执行refresh note相关业务流程。

        参数：
        - note_id（str）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - title（str）：调用方传入的title数据或控制参数，用于驱动本函数处理流程。
        - content（str）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

        返回：int；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        if not content.strip():
            await self.repository.delete_source(user_id=user_id, source_type="note", source_id=note_id)
            return 0
        return await self.upsert_note(note_id, user_id, title, content)

    async def delete_note(self, note_id: str, user_id: str) -> None:
        """
        用途：删除delete note相关的数据或流程。

        参数：
        - note_id（str）：调用方传入的note_id数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self.repository.delete_source(user_id=user_id, source_type="note", source_id=note_id)
