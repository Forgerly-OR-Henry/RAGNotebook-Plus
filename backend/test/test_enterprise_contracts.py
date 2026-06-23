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
    with pytest.raises(ValidationError):
        MindMapGenerateRequest(**payload)


def test_mindmap_response_contract():
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
