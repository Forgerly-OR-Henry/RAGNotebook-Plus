"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import pytest
from pydantic import ValidationError

from mvc.schemas import (
    MindMapGenerateRequest,
    MindMapNode,
    MindMapResponse,
    QuickTestCreateRequest,
    SourceCitation,
)


def test_quick_test_create_request_contract():
    """
    用途：执行test quick test create request contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payload = QuickTestCreateRequest(
        source_type="mixed",
        source_ids=["note-1", "doc-1.pdf"],
        question_count=3,
        difficulty="normal",
        focus="核心概念",
    )

    assert payload.source_type == "mixed"
    assert payload.question_count == 3
    assert payload.difficulty == "normal"


def test_mindmap_generate_request_contract():
    """
    用途：执行test mindmap generate request contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    payload = MindMapGenerateRequest(
        source_type="note",
        source_ids=["note-1", "note-2"],
        max_nodes=40,
        max_depth=4,
    )

    assert payload.source_type == "note"
    assert payload.source_ids == ["note-1", "note-2"]
    assert payload.max_nodes == 40
    assert payload.max_depth == 4


@pytest.mark.parametrize(
    "payload",
    [
        {"source_type": "note", "source_ids": [], "max_nodes": 40, "max_depth": 4},
        {"source_type": "note", "source_ids": [f"note-{idx}" for idx in range(21)], "max_nodes": 40, "max_depth": 4},
        {"source_type": "mixed", "source_ids": ["note-1"], "max_nodes": 40, "max_depth": 4},
    ],
)
def test_mindmap_generate_request_rejects_invalid_source_scope(payload):
    """
    用途：执行test mindmap generate request rejects invalid source scope相关业务逻辑。

    参数：
    - payload（未显式标注）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    with pytest.raises(ValidationError):
        MindMapGenerateRequest(**payload)


def test_mindmap_response_contract():
    """
    用途：执行test mindmap response contract相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    citation = SourceCitation(
        source_type="note",
        source_id="note-1",
        title="测试笔记",
        chunk_id="note-1",
        quote="引用片段",
        score=0.91,
    )
    response = MindMapResponse(
        mindmap_id="map-1",
        title="测试导图",
        source_type="note",
        source_ids=["note-1"],
        nodes=[MindMapNode(id="n1", label="根节点", level=0, type="root", source_refs=[])],
        edges=[],
        citations=[citation],
        source_refs=[{"id": "note-1", "type": "note", "title": "测试笔记"}],
        version=1,
    )

    assert response.nodes[0].label == "根节点"
    assert response.citations[0].source_type == "note"
