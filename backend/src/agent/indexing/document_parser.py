"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass

from langchain_core.documents import Document

from agent.rag.document_handler.processor import DocumentProcessor


@dataclass
class ParsedDocument:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - content_hash（str）：保存content_hash相关状态、配置或数据字段。
    - documents（list[Document]）：保存documents相关状态、配置或数据字段。
    """
    content_hash: str
    documents: list[Document]


class DocumentParser:
    """File parsing and chunking adapter independent of vector persistence."""

    def __init__(self, embed_model=None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - embed_model（未显式标注）：调用方传入的embed_model数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.processor = DocumentProcessor(embed_model=embed_model)

    def parse_bytes_sync(
        self,
        *,
        content: bytes,
        filename: str,
        user_id: str,
        use_multimodal: bool = False,
    ) -> ParsedDocument:
        """
        用途：解析parse bytes sync相关的数据或流程。

        参数：
        - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
        - filename（str）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - use_multimodal（bool）：调用方传入的use_multimodal数据或控制参数，用于驱动本函数处理流程。

        返回：ParsedDocument；返回值供调用方继续编排业务流程或生成接口响应。
        """
        suffix = os.path.splitext(filename or "")[1]
        content_hash = hashlib.sha256(content).hexdigest()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(content)
                temp_path = handle.name

            documents = self.processor.get_file_document_sync(
                temp_path,
                content_hash=content_hash,
                user_id=user_id,
                use_multimodal=use_multimodal,
            )
            if not documents or not any(doc.page_content.strip() for doc in documents):
                raise ValueError("文件未解析到可索引文本内容，请确认文件未损坏或另存为新版格式后重试")
            split_docs = self.processor.split_documents_sync(documents) if documents else []
            if not split_docs:
                raise ValueError("文件切片为空，请确认文件包含可识别文本")
            return ParsedDocument(content_hash=content_hash, documents=split_docs)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
