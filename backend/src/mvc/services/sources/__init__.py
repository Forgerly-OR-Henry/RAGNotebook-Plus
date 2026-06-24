"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.services.sources.models import SourceChunk, format_source_context
from mvc.services.sources.registry import SourceRegistry, get_source_registry

__all__ = ["SourceChunk", "SourceRegistry", "format_source_context", "get_source_registry"]
