"""
模块职责：Agent 能力模块，负责检索增强、模型调用、工具编排或文档处理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import json
from dataclasses import asdict, dataclass

EVENT_RESPONSE = "response"
EVENT_ERROR = "error"
EVENT_DONE = "done"


@dataclass
class SSEEvent:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - event_type（str）：保存event_type相关状态、配置或数据字段。
    - message（str）：保存message相关状态、配置或数据字段。
    - total_files（int）：保存total_files相关状态、配置或数据字段。
    - file_index（int | None）：保存file_index相关状态、配置或数据字段。
    - filename（str | None）：保存filename相关状态、配置或数据字段。
    - step（str | None）：保存step相关状态、配置或数据字段。
    - progress（int）：保存progress相关状态、配置或数据字段。
    - success_count（int）：保存success_count相关状态、配置或数据字段。
    - failed_count（int）：保存failed_count相关状态、配置或数据字段。
    - slice_success_count（int）：保存slice_success_count相关状态、配置或数据字段。
    - error_message（str | None）：保存error_message相关状态、配置或数据字段。
    - chunk_count（int | None）：保存chunk_count相关状态、配置或数据字段。
    - document_id（str | None）：保存document_id相关状态、配置或数据字段。
    """
    event_type: str
    message: str
    total_files: int = 0
    file_index: int | None = None
    filename: str | None = None
    step: str | None = None
    progress: int = 0
    success_count: int = 0
    failed_count: int = 0
    slice_success_count: int = 0
    error_message: str | None = None
    chunk_count: int | None = None
    document_id: str | None = None

    def to_sse(self) -> str:
        """
        用途：执行to sse相关业务逻辑。

        参数：无显式业务参数。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        payload = {k: v for k, v in asdict(self).items() if v is not None}
        return f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class SliceResult:
    """切片结果数据结构"""

    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.file_index: int = 0
        self.filename: str = ""
        self.documents: list = []
        self.content_hash: str = ""
        self.success: bool = False
        self.error: str | None = None
        self.chunk_count: int = 0

    @classmethod
    def success_result(cls, file_index: int, filename: str, documents: list, content_hash: str) -> 'SliceResult':
        """
        用途：执行success result相关业务逻辑。

        参数：
        - file_index（int）：调用方传入的file_index数据或控制参数，用于驱动本函数处理流程。
        - filename（str）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - documents（list）：调用方传入的documents数据或控制参数，用于驱动本函数处理流程。
        - content_hash（str）：调用方传入的content_hash数据或控制参数，用于驱动本函数处理流程。

        返回：'SliceResult'；返回值供调用方继续编排业务流程或生成接口响应。
        """
        result = cls()
        result.file_index = file_index
        result.filename = filename
        result.documents = documents
        result.content_hash = content_hash
        result.success = True
        result.chunk_count = len(documents)
        return result

    @classmethod
    def error_result(cls, file_index: int, filename: str, error: str) -> 'SliceResult':
        """
        用途：执行error result相关业务逻辑。

        参数：
        - file_index（int）：调用方传入的file_index数据或控制参数，用于驱动本函数处理流程。
        - filename（str）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - error（str）：调用方传入的error数据或控制参数，用于驱动本函数处理流程。

        返回：'SliceResult'；返回值供调用方继续编排业务流程或生成接口响应。
        """
        result = cls()
        result.file_index = file_index
        result.filename = filename
        result.success = False
        result.error = error
        return result

    def to_dict(self) -> dict:
        """
        用途：执行to dict相关业务逻辑。

        参数：无显式业务参数。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return {
            'file_index': self.file_index,
            'filename': self.filename,
            'documents': self.documents,
            'content_hash': self.content_hash,
            'success': self.success,
            'error': self.error,
            'chunk_count': self.chunk_count
        }
