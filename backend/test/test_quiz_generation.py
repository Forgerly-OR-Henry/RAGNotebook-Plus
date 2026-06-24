"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio

from mvc.schemas import QuizGenerateRequest
from mvc.services.quiz_service import QuizGenerationError, QuizService
from mvc.services.sources.models import SourceChunk


class FakeCollector:
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：
    - chunks（实例属性，由构造函数注入或初始化）：保存chunks相关状态、配置或数据字段。
    - calls（实例属性，由构造函数注入或初始化）：保存calls相关状态、配置或数据字段。
    """
    def __init__(self, chunks):
        """
        用途：执行init相关业务逻辑。

        参数：
        - chunks（未显式标注）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.chunks = chunks
        self.calls = []

    async def collect(self, db, user_id, source_type, source_ids, max_chunks=12):
        """
        用途：异步执行collect相关业务流程。

        参数：
        - db（未显式标注）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（未显式标注）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - source_type（未显式标注）：调用方传入的source_type数据或控制参数，用于驱动本函数处理流程。
        - source_ids（未显式标注）：调用方传入的source_ids数据或控制参数，用于驱动本函数处理流程。
        - max_chunks（未显式标注）：调用方传入的max_chunks数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        self.calls.append((user_id, source_type, tuple(source_ids), max_chunks))
        return [chunk for chunk in self.chunks if chunk.source_type == source_type and chunk.source_id in source_ids][:max_chunks]


class FakeQuizService(QuizService):
    """
    用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

    属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
    """
    async def _model_json(self, prompt):
        """
        用途：异步执行model json相关业务流程。

        参数：
        - prompt（未显式标注）：调用方传入的prompt数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return {
            "title": "资料测验",
            "description": "基于资料",
            "questions": [
                {
                    "id": "q1",
                    "type": "single_choice",
                    "question": "核心内容是什么？",
                    "options": ["A", "B", "C", "D"],
                    "answer": "B",
                    "explanation": "依据资料。",
                }
            ],
        }


def test_quiz_generate_request_contract():
    """
    用途：执行test quiz generate request contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payload = QuizGenerateRequest(selected_notes=["note-1"], selected_files=["doc-1"])

    assert payload.selected_notes == ["note-1"]
    assert payload.selected_files == ["doc-1"]


def test_quiz_service_generates_quiz_from_selected_sources():
    """
    用途：执行test quiz service generates quiz from selected sources相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    chunks = [
        SourceChunk(source_type="note", source_id="note-1", title="笔记", content="核心内容"),
        SourceChunk(source_type="knowledge", source_id="doc-1", title="文档", content="知识库内容"),
    ]
    service = FakeQuizService(collector=FakeCollector(chunks))
    payload = QuizGenerateRequest(selected_notes=["note-1"], selected_files=["doc-1"])

    quiz = asyncio.run(service.generate_quiz(None, "user-1", payload))

    assert quiz.title == "资料测验"
    assert quiz.questions[0].answer == "B"
    assert service.collector.calls[0][:3] == ("user-1", "note", ("note-1",))
    assert service.collector.calls[1][:3] == ("user-1", "knowledge", ("doc-1",))


def test_quiz_service_rejects_empty_selected_content():
    """
    用途：执行test quiz service rejects empty selected content相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    service = QuizService(collector=FakeCollector([]))
    payload = QuizGenerateRequest(selected_notes=["missing"])

    try:
        asyncio.run(service.generate_quiz(None, "user-1", payload))
    except QuizGenerationError as exc:
        assert "无法生成测验" in str(exc)
    else:
        raise AssertionError("expected QuizGenerationError")
