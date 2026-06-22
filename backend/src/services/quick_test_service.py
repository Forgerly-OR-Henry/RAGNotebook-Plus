from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.background_init import init_manager
from core.logger_handler import logger
from models.study_test import StudyTestSession, StudyTestTurn
from schemas import QuickTestCreateRequest
from services.sources import SourceChunk, format_source_context, get_source_registry


def _extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


class QuickTestService:
    def __init__(self):
        self.collector = get_source_registry()

    async def create_session(self, db: AsyncSession, user_id: str, payload: QuickTestCreateRequest) -> dict:
        chunks = await self.collector.collect(db, user_id, payload.source_type, payload.source_ids)
        if not chunks:
            raise ValueError("没有找到可用于快速测试的来源内容")

        session_id = str(uuid.uuid4())
        question = await self._generate_question(chunks, payload.difficulty, payload.focus, turn_index=1)
        citations = [chunk.citation() for chunk in chunks[:3]]

        session = StudyTestSession(
            id=session_id,
            user_id=user_id,
            source_type=payload.source_type,
            source_ids=payload.source_ids,
            question_count=max(1, min(payload.question_count, 20)),
            difficulty=payload.difficulty,
            focus=payload.focus,
            status="active",
            current_turn=1,
            weak_points=[],
            recommended_refs=[],
        )
        turn = StudyTestTurn(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            turn_index=1,
            question=question,
            citations=citations,
        )
        db.add(session)
        db.add(turn)
        await db.commit()
        return {"session_id": session_id, "first_question": question, "citations": citations}

    async def answer(self, db: AsyncSession, user_id: str, session_id: str, answer: str) -> dict | None:
        session = await self._get_session_orm(db, user_id, session_id)
        if not session:
            return None

        turn = await self._get_current_turn(db, user_id, session_id, session.current_turn)
        if not turn:
            return None

        chunks = await self.collector.collect(db, user_id, session.source_type, session.source_ids)
        evaluation = await self._evaluate_answer(chunks, turn.question, answer)
        turn.answer = answer
        turn.feedback = evaluation["feedback"]
        turn.score = evaluation["score"]
        turn.citations = evaluation["citations"]

        is_finished = session.current_turn >= session.question_count
        next_question = None
        citations = evaluation["citations"]
        if is_finished:
            final = await self._finish_payload(db, session, chunks)
            session.status = "completed"
            session.summary = final["final_summary"]
            session.weak_points = final["weak_points"]
            session.recommended_refs = final["recommended_notes"] + final["recommended_documents"]
            session.completed_at = datetime.now()
        else:
            session.current_turn += 1
            next_question = await self._generate_question(
                chunks,
                session.difficulty,
                session.focus,
                turn_index=session.current_turn,
                previous_question=turn.question,
                previous_answer=answer,
            )
            next_turn = StudyTestTurn(
                id=str(uuid.uuid4()),
                session_id=session.id,
                user_id=user_id,
                turn_index=session.current_turn,
                question=next_question,
                citations=[chunk.citation() for chunk in chunks[:3]],
            )
            db.add(next_turn)

        await db.commit()
        return {
            "feedback": evaluation["feedback"],
            "score": evaluation["score"],
            "next_question": next_question,
            "citations": citations,
            "is_finished": is_finished,
        }

    async def get_session(self, db: AsyncSession, user_id: str, session_id: str) -> dict | None:
        session = await self._get_session_orm(db, user_id, session_id)
        if not session:
            return None
        turns_result = await db.execute(
            select(StudyTestTurn)
            .where(StudyTestTurn.session_id == session_id, StudyTestTurn.user_id == user_id)
            .order_by(StudyTestTurn.turn_index.asc())
        )
        turns = turns_result.scalars().all()
        return {
            "session_id": session.id,
            "source_type": session.source_type,
            "source_ids": session.source_ids or [],
            "question_count": session.question_count,
            "difficulty": session.difficulty,
            "focus": session.focus,
            "status": session.status,
            "current_turn": session.current_turn,
            "summary": session.summary,
            "weak_points": session.weak_points or [],
            "recommended_refs": session.recommended_refs or [],
            "turns": [
                {
                    "id": turn.id,
                    "turn_index": turn.turn_index,
                    "question": turn.question,
                    "answer": turn.answer,
                    "feedback": turn.feedback,
                    "score": turn.score,
                    "citations": turn.citations or [],
                    "created_at": str(turn.created_at) if turn.created_at else None,
                }
                for turn in turns
            ],
            "created_at": str(session.created_at) if session.created_at else None,
            "updated_at": str(session.updated_at) if session.updated_at else None,
        }

    async def finish(self, db: AsyncSession, user_id: str, session_id: str) -> dict | None:
        session = await self._get_session_orm(db, user_id, session_id)
        if not session:
            return None
        chunks = await self.collector.collect(db, user_id, session.source_type, session.source_ids)
        final = await self._finish_payload(db, session, chunks)
        session.status = "completed"
        session.summary = final["final_summary"]
        session.weak_points = final["weak_points"]
        session.recommended_refs = final["recommended_notes"] + final["recommended_documents"]
        session.completed_at = datetime.now()
        await db.commit()
        return final

    async def _get_session_orm(self, db: AsyncSession, user_id: str, session_id: str):
        result = await db.execute(
            select(StudyTestSession).where(StudyTestSession.id == session_id, StudyTestSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_current_turn(self, db: AsyncSession, user_id: str, session_id: str, turn_index: int):
        result = await db.execute(
            select(StudyTestTurn).where(
                StudyTestTurn.session_id == session_id,
                StudyTestTurn.user_id == user_id,
                StudyTestTurn.turn_index == turn_index,
            )
        )
        return result.scalar_one_or_none()

    async def _model_json(self, prompt: str) -> dict | None:
        try:
            await asyncio.wait_for(init_manager.models_ready.wait(), timeout=20)
            response = await init_manager.chat_model.ainvoke([HumanMessage(content=prompt)])
            return _extract_json(response.content.strip())
        except Exception as exc:
            logger.warning(f"快速测试 LLM JSON 生成失败，使用降级逻辑: {exc}")
            return None

    async def _generate_question(
        self,
        chunks: list[SourceChunk],
        difficulty: str,
        focus: str | None,
        turn_index: int,
        previous_question: str | None = None,
        previous_answer: str | None = None,
    ) -> str:
        context = format_source_context(chunks)
        prompt = f"""你是企业级笔记学习助手。请基于资料生成第 {turn_index} 个口头问答问题。
难度: {difficulty}
关注点: {focus or "综合理解"}
上一题: {previous_question or "无"}
上一题回答: {previous_answer or "无"}
资料:
{context}

只返回 JSON: {{"question": "一个清晰、可口头回答的问题"}}"""
        data = await self._model_json(prompt)
        if data and data.get("question"):
            return str(data["question"])
        title = chunks[0].title if chunks else "当前资料"
        return f"请用自己的话概括「{title}」中最重要的概念，并说明它为什么重要？"

    async def _evaluate_answer(self, chunks: list[SourceChunk], question: str, answer: str) -> dict:
        context = format_source_context(chunks)
        prompt = f"""你是严格但友好的学习测评助手。请根据资料评价用户回答。
问题: {question}
用户回答: {answer}
资料:
{context}

只返回 JSON:
{{"feedback": "反馈和改进建议", "score": 0到100的整数}}"""
        data = await self._model_json(prompt) or {}
        score = data.get("score", 60)
        try:
            score = max(0, min(int(score), 100))
        except Exception:
            score = 60
        feedback = data.get("feedback") or "已记录回答。建议回到资料中的关键定义、因果关系和例子继续补充。"
        return {"feedback": str(feedback), "score": score, "citations": [chunk.citation() for chunk in chunks[:3]]}

    async def _finish_payload(self, db: AsyncSession, session: StudyTestSession, chunks: list[SourceChunk]) -> dict:
        turns_result = await db.execute(
            select(StudyTestTurn)
            .where(StudyTestTurn.session_id == session.id, StudyTestTurn.user_id == session.user_id)
            .order_by(StudyTestTurn.turn_index.asc())
        )
        turns = turns_result.scalars().all()
        qa = "\n".join(f"Q:{turn.question}\nA:{turn.answer or ''}\nScore:{turn.score or 0}" for turn in turns)
        prompt = f"""请总结这次口头快速测试。
测试记录:
{qa}

只返回 JSON:
{{"final_summary": "总体掌握情况", "weak_points": ["薄弱点1", "薄弱点2"]}}"""
        data = await self._model_json(prompt) or {}
        citations = [chunk.citation() for chunk in chunks[:3]]
        return {
            "final_summary": data.get("final_summary") or "本次快速测试已完成。建议重点复盘得分较低的问题和对应资料片段。",
            "weak_points": data.get("weak_points") or [],
            "recommended_notes": [c for c in citations if c["source_type"] == "note"],
            "recommended_documents": [c for c in citations if c["source_type"] == "knowledge"],
        }
