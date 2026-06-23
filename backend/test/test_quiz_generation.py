import asyncio

from mvc.schemas import QuizGenerateRequest
from mvc.services.quiz_service import QuizGenerationError, QuizService
from mvc.services.sources.models import SourceChunk


class FakeCollector:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    async def collect(self, db, user_id, source_type, source_ids, max_chunks=12):
        self.calls.append((user_id, source_type, tuple(source_ids), max_chunks))
        return [chunk for chunk in self.chunks if chunk.source_type == source_type and chunk.source_id in source_ids][:max_chunks]


class FakeQuizService(QuizService):
    async def _model_json(self, prompt):
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
    payload = QuizGenerateRequest(selected_notes=["note-1"], selected_files=["doc-1"])

    assert payload.selected_notes == ["note-1"]
    assert payload.selected_files == ["doc-1"]


def test_quiz_service_generates_quiz_from_selected_sources():
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
    service = QuizService(collector=FakeCollector([]))
    payload = QuizGenerateRequest(selected_notes=["missing"])

    try:
        asyncio.run(service.generate_quiz(None, "user-1", payload))
    except QuizGenerationError as exc:
        assert "无法生成测验" in str(exc)
    else:
        raise AssertionError("expected QuizGenerationError")
