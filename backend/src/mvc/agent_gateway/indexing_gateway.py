"""
模块职责：AI 网关模块，负责把业务服务与模型、索引或 Agent 能力解耦。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from agent.indexing.document_parser import DocumentParser
from agent.indexing.index_repository import IndexChunk, IndexRepository, assert_embedding_dimension
from agent.rag.sse_models import SSEEvent

__all__ = ["DocumentParser", "IndexChunk", "IndexRepository", "SSEEvent", "assert_embedding_dimension"]
