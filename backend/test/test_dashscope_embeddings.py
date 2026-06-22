import sys
from http import HTTPStatus
from types import SimpleNamespace

import pytest

from app.utils.factory import DashScopeEmbeddingsWrapper


def test_dashscope_embedding_passes_configured_dimension(monkeypatch):
    calls = []

    class FakeTextEmbedding:
        @staticmethod
        def call(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(status_code=HTTPStatus.OK, output={"embeddings": [{"embedding": [0.1, 0.2, 0.3]}]})

    fake_dashscope = SimpleNamespace(TextEmbedding=FakeTextEmbedding, api_key=None)
    monkeypatch.setitem(sys.modules, "dashscope", fake_dashscope)

    wrapper = DashScopeEmbeddingsWrapper(api_key="test-key", embedding_dim=3)

    assert wrapper.embed_query("hello") == [0.1, 0.2, 0.3]
    assert fake_dashscope.api_key == "test-key"
    assert calls == [{"model": "text-embedding-v4", "input": "hello", "dimension": 3}]


def test_dashscope_embedding_raises_real_provider_error(monkeypatch):
    class FakeTextEmbedding:
        @staticmethod
        def call(**kwargs):
            return SimpleNamespace(status_code=400, code="InvalidParameter", message="Model not exist.")

    monkeypatch.setitem(sys.modules, "dashscope", SimpleNamespace(TextEmbedding=FakeTextEmbedding, api_key=None))
    wrapper = DashScopeEmbeddingsWrapper(model_name="bad-model", api_key="test-key", embedding_dim=1024)

    with pytest.raises(RuntimeError, match="Model not exist"):
        wrapper.embed_query("hello")
