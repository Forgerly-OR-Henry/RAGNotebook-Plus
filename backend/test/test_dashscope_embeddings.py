"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import sys
from http import HTTPStatus
from types import SimpleNamespace

import pytest

from agent.models.factory import DashScopeEmbeddingsWrapper


def test_dashscope_embedding_passes_configured_dimension(monkeypatch):
    """
    用途：执行test dashscope embedding passes configured dimension相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    calls = []

    class FakeTextEmbedding:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        @staticmethod
        def call(**kwargs):
            """
            用途：执行call相关业务逻辑。

            参数：
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            calls.append(kwargs)
            return SimpleNamespace(status_code=HTTPStatus.OK, output={"embeddings": [{"embedding": [0.1, 0.2, 0.3]}]})

    fake_dashscope = SimpleNamespace(TextEmbedding=FakeTextEmbedding, api_key=None)
    monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)

    wrapper = DashScopeEmbeddingsWrapper(api_key="test-key", embedding_dim=3)

    assert wrapper.embed_query("hello") == [0.1, 0.2, 0.3]
    assert fake_dashscope.api_key == "test-key"
    assert calls == [{"model": "text-embedding-v4", "input": "hello", "dimension": 3}]


def test_dashscope_embedding_raises_real_provider_error(monkeypatch):
    """
    用途：执行test dashscope embedding raises real provider error相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    class FakeTextEmbedding:
        """
        用途：测试替身或测试数据结构，用于隔离外部依赖并验证目标行为。

        属性：该类不声明持久字段，主要通过方法行为或异常类型表达语义。
        """
        @staticmethod
        def call(**kwargs):
            """
            用途：执行call相关业务逻辑。

            参数：
            - kwargs（未显式标注）：调用方传入的kwargs数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            return SimpleNamespace(status_code=400, code="InvalidParameter", message="Model not exist.")

    monkeypatch.setitem(sys.modules, "dashscope", SimpleNamespace(TextEmbedding=FakeTextEmbedding, api_key=None))
    wrapper = DashScopeEmbeddingsWrapper(model_name="bad-model", api_key="test-key", embedding_dim=1024)

    with pytest.raises(RuntimeError, match="Model not exist"):
        wrapper.embed_query("hello")
