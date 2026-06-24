"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio

from langchain_core.documents import Document

from agent.rag.document_handler import processor as processor_module
from agent.rag.document_handler.processor import DocumentProcessor


def test_pdf_upload_loader_skips_multimodal_when_disabled(monkeypatch):
    """
    用途：执行test pdf upload loader skips multimodal when disabled相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    calls = []

    async def fake_pdf_loader(path):
        """
        用途：异步执行fake pdf loader相关业务流程。

        参数：
        - path（未显式标注）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        calls.append(("plain", path))
        return [Document(page_content="plain pdf")]

    async def fake_multimodal_loader(path, content_hash, user_id):
        """
        用途：异步执行fake multimodal loader相关业务流程。

        参数：
        - path（未显式标注）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
        - content_hash（未显式标注）：调用方传入的content_hash数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        calls.append(("multimodal", path, content_hash, user_id))
        return [Document(page_content="vision pdf")]

    monkeypatch.setattr(processor_module, "pdf_loader", fake_pdf_loader)
    monkeypatch.setattr(processor_module, "pdf_multimodal_loader", fake_multimodal_loader)

    processor = DocumentProcessor.__new__(DocumentProcessor)
    result = asyncio.run(
        processor.get_file_document(
            "lecture.pdf",
            content_hash="hash-1",
            user_id="user-1",
            use_multimodal=False,
        )
    )

    assert result[0].page_content == "plain pdf"
    assert calls == [("plain", "lecture.pdf")]


def test_pdf_loader_keeps_multimodal_path_when_enabled(monkeypatch):
    """
    用途：执行test pdf loader keeps multimodal path when enabled相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    calls = []

    async def fake_pdf_loader(path):
        """
        用途：异步执行fake pdf loader相关业务流程。

        参数：
        - path（未显式标注）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        calls.append(("plain", path))
        return [Document(page_content="plain pdf")]

    async def fake_multimodal_loader(path, content_hash, user_id):
        """
        用途：异步执行fake multimodal loader相关业务流程。

        参数：
        - path（未显式标注）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
        - content_hash（未显式标注）：调用方传入的content_hash数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        calls.append(("multimodal", path, content_hash, user_id))
        return [Document(page_content="vision pdf")]

    monkeypatch.setattr(processor_module, "pdf_loader", fake_pdf_loader)
    monkeypatch.setattr(processor_module, "pdf_multimodal_loader", fake_multimodal_loader)

    processor = DocumentProcessor.__new__(DocumentProcessor)
    result = asyncio.run(
        processor.get_file_document(
            "lecture.pdf",
            content_hash="hash-1",
            user_id="user-1",
            use_multimodal=True,
        )
    )

    assert result[0].page_content == "vision pdf"
    assert calls == [("multimodal", "lecture.pdf", "hash-1", "user-1")]
