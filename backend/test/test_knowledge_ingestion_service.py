"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio

import pytest

from mvc.models.document import Document
from mvc.models.storage_object import StorageObject
from mvc.services.knowledge_ingestion_service import KnowledgeIngestionService


class FakeUploadFile:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - filename（实例属性，由构造函数注入或初始化）：保存filename相关状态、配置或数据字段。
    - _content（实例属性，由构造函数注入或初始化）：保存_content相关状态、配置或数据字段。
    """
    def __init__(self, filename: str, content: bytes):
        """
        用途：执行init相关业务逻辑。

        参数：
        - filename（str）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.filename = filename
        self._content = content

    async def read(self):
        """
        用途：异步执行read相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return self._content

    async def seek(self, offset):
        """
        用途：异步执行seek相关业务流程。

        参数：
        - offset（未显式标注）：调用方传入的offset数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return None


def test_cancelled_upload_cleans_partial_knowledge_document(monkeypatch):
    """
    用途：执行test cancelled upload cleans partial knowledge document相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    class FakeStorageService:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        async def upload_bytes(self, *, kind, user_id, object_id, filename, content, mime_type):
            """
            用途：上传upload bytes相关的数据或流程。

            参数：
            - kind（未显式标注）：调用方传入的kind数据或控制参数，用于驱动本函数处理流程。
            - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
            - object_id（未显式标注）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。
            - filename（未显式标注）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
            - content（未显式标注）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
            - mime_type（未显式标注）：调用方传入的mime_type数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            return StorageObject(
                id=object_id,
                backend="local",
                host="local",
                storage_uri=f"local://{kind}/{user_id}/{object_id}.md",
                storage_path=f"{kind}/{user_id}/{object_id}.md",
                original_filename=filename,
                mime_type=mime_type,
                file_ext=".md",
                checksum_sha256="hash",
                size_bytes=len(content),
            )

        async def read_object_bytes(self, storage_object):
            """
            用途：异步执行read object bytes相关业务流程。

            参数：
            - storage_object（未显式标注）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

            副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
            """
            raise asyncio.CancelledError()

    cleanup_calls = []
    service = KnowledgeIngestionService(storage_service=FakeStorageService())

    async def fake_create_document_record(**kwargs):
        """
        用途：异步执行fake create document record相关业务流程。

        参数：
        - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return Document(
            id=kwargs["document_id"],
            user_id=kwargs["user_id"],
            source_type="knowledge",
            title=kwargs["filename"],
            storage_object_id=kwargs["storage_object"].id,
            content_hash=kwargs["content_hash"],
            file_size=kwargs["file_size"],
            mime_type=kwargs["mime_type"],
            file_ext=".md",
            status="pending",
        )

    async def fake_cleanup_partial_document(**kwargs):
        """
        用途：异步执行fake cleanup partial document相关业务流程。

        参数：
        - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        cleanup_calls.append(kwargs)

    monkeypatch.setattr(service, "_create_document_record", fake_create_document_record)
    monkeypatch.setattr(service, "_cleanup_partial_document", fake_cleanup_partial_document)

    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        stream = service.upload_stream([FakeUploadFile("retry.md", b"# retry")], "user-1")
        await stream.__anext__()
        with pytest.raises(asyncio.CancelledError):
            async for _ in stream:
                pass

    asyncio.run(scenario())

    assert len(cleanup_calls) == 1
    assert cleanup_calls[0]["user_id"] == "user-1"
    assert cleanup_calls[0]["storage_object"].original_filename == "retry.md"


def test_upload_timeout_raises_reader_friendly_error():
    """
    用途：执行test upload timeout raises reader friendly error相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async def scenario():
        """
        用途：异步执行scenario相关业务流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        with pytest.raises(TimeoutError, match="写入索引超时"):
            await KnowledgeIngestionService._with_timeout(
                asyncio.sleep(1),
                timeout_seconds=0.01,
                timeout_message="写入索引超时",
            )

    asyncio.run(scenario())
