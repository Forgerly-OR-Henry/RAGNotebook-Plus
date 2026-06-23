from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.agent_gateway.quick_test_ai_gateway import model_json
from mvc.models.document import Document
from mvc.schemas.chat import QuizGenerateRequest, QuizQuestion, QuizResponse
from mvc.services.sources import SourceChunk, format_source_context, get_source_registry


MAX_CONTEXT_CHARS = 40000
DEFAULT_QUESTION_COUNT = 5


class QuizGenerationError(ValueError):
    """Raised when no selected content can be used to generate a quiz."""


class QuizService:
    def __init__(self, collector=None):
        self.collector = collector or get_source_registry()

    async def generate_quiz(self, db: AsyncSession, user_id: str, payload: QuizGenerateRequest) -> QuizResponse:
        note_ids = _dedupe(payload.selected_notes)
        knowledge_refs = _dedupe(payload.selected_files)
        knowledge_ids = await self._resolve_knowledge_source_ids(db, user_id, knowledge_refs)

        chunks: list[SourceChunk] = []
        if note_ids:
            chunks.extend(await self.collector.collect(db, user_id, "note", note_ids, max_chunks=max(12, len(note_ids))))
        if knowledge_ids:
            chunks.extend(await self.collector.collect(db, user_id, "knowledge", knowledge_ids, max_chunks=30))

        if not chunks:
            raise QuizGenerationError("未找到选中的笔记或知识库文档内容，无法生成测验")

        return await self._generate_from_chunks(chunks)

    async def _resolve_knowledge_source_ids(self, db: AsyncSession | None, user_id: str, source_refs: list[str]) -> list[str]:
        if not source_refs:
            return []
        if db is None:
            return source_refs

        result = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.source_type == "knowledge",
                or_(Document.id.in_(source_refs), Document.title.in_(source_refs)),
            )
        )
        ref_to_id: dict[str, str] = {}
        for document in result.scalars().all():
            if document.id in source_refs:
                ref_to_id[document.id] = document.id
            if document.title in source_refs:
                ref_to_id[document.title] = document.id

        return _dedupe(ref_to_id.get(ref, ref) for ref in source_refs)

    async def _generate_from_chunks(self, chunks: list[SourceChunk]) -> QuizResponse:
        context = format_source_context(chunks, max_chars=MAX_CONTEXT_CHARS)
        prompt = f"""你是一个智能学习助手。请根据以下资料生成一个包含 {DEFAULT_QUESTION_COUNT} 道题的快速测验，题型包含单选题和判断题。
要求:
1. 题目必须来自资料内容，避免泛泛而谈。
2. 单选题提供 4 个选项，判断题提供 ["正确", "错误"]。
3. answer 必须与 options 中某一项完全一致。
4. explanation 用一两句话说明答案依据。
5. 只返回 JSON，不要返回 Markdown 代码块或额外说明。

JSON 格式:
{{
  "title": "测验标题",
  "description": "基于所选资料生成的快速测验",
  "questions": [
    {{
      "id": "q1",
      "type": "single_choice",
      "question": "问题内容",
      "options": ["选项 A", "选项 B", "选项 C", "选项 D"],
      "answer": "正确选项完整文本",
      "explanation": "答案解析"
    }}
  ]
}}

资料:
{context}
"""
        data = await self._model_json(prompt)
        if data:
            quiz = self._coerce_quiz(data)
            if quiz is not None:
                return quiz
        return self._fallback_quiz(chunks)

    async def _model_json(self, prompt: str) -> dict | None:
        return await model_json(prompt)

    def _coerce_quiz(self, data: dict) -> QuizResponse | None:
        questions = data.get("questions")
        if not isinstance(questions, list):
            return None

        normalized: list[QuizQuestion] = []
        for idx, raw in enumerate(questions[:DEFAULT_QUESTION_COUNT], 1):
            if not isinstance(raw, dict):
                continue
            question = str(raw.get("question") or "").strip()
            options = [str(option).strip() for option in raw.get("options") or [] if str(option).strip()]
            answer = str(raw.get("answer") or "").strip()
            if not question or not options:
                continue
            if answer not in options:
                answer = options[0]
            qtype = str(raw.get("type") or ("true_false" if len(options) == 2 else "single_choice"))
            normalized.append(
                QuizQuestion(
                    id=str(raw.get("id") or f"q{idx}"),
                    type=qtype,
                    question=question,
                    options=options,
                    answer=answer,
                    explanation=str(raw.get("explanation") or ""),
                )
            )

        if not normalized:
            return None
        return QuizResponse(
            title=str(data.get("title") or "快速测验"),
            description=str(data.get("description") or "基于所选资料生成的快速测验"),
            questions=normalized,
        )

    @staticmethod
    def _fallback_quiz(chunks: list[SourceChunk]) -> QuizResponse:
        questions: list[QuizQuestion] = []
        usable_chunks = chunks or [SourceChunk(source_type="note", source_id="fallback", title="当前资料", content="")]
        for idx in range(DEFAULT_QUESTION_COUNT):
            chunk = usable_chunks[idx % len(usable_chunks)]
            snippet = " ".join(chunk.content.split())[:180] or chunk.title
            if idx % 2 == 0:
                options = ["核心概念与关键依据", "界面配色方案", "账号登录流程", "无关背景信息"]
                qtype = "single_choice"
                answer = options[0]
                question = f"以下哪一项最适合作为《{chunk.title}》的复习重点？"
            else:
                options = ["正确", "错误"]
                qtype = "true_false"
                answer = "正确"
                question = f"《{chunk.title}》中的内容可以作为本次测验的复习依据。"
            questions.append(
                QuizQuestion(
                    id=f"q{idx + 1}",
                    type=qtype,
                    question=question,
                    options=options,
                    answer=answer,
                    explanation=f"依据资料片段：{snippet}",
                )
            )
        return QuizResponse(title="快速测验", description="基于所选资料生成的快速测验", questions=questions)


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


_quiz_service: QuizService | None = None


def get_quiz_service() -> QuizService:
    global _quiz_service
    if _quiz_service is None:
        _quiz_service = QuizService()
    return _quiz_service
