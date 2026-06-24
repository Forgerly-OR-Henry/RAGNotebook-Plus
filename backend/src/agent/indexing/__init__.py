"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from agent.indexing.document_parser import DocumentParser
from agent.indexing.index_repository import IndexChunk, IndexRepository, assert_embedding_dimension

__all__ = ["DocumentParser", "IndexChunk", "IndexRepository", "assert_embedding_dimension"]
