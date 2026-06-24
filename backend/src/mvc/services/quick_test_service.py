"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mvc.agent_gateway.quick_test_ai_gateway import model_json
from mvc.models.study_test import StudyTestSession, StudyTestTurn
from mvc.schemas import QuickTestCreateRequest
from mvc.services.sources import SourceChunk, format_source_context, get_source_registry


class QuickTestService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - collector（实例属性，由构造函数注入或初始化）：保存collector相关状态、配置或数据字段。
    """
    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.collector = get_source_registry()

    async def create_session(self, db: AsyncSession, user_id: str, payload: QuickTestCreateRequest) -> dict:
        """
        用途：创建create session相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - payload（QuickTestCreateRequest）：调用方传入的payload数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行answer相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
        - answer（str）：调用方传入的answer数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：读取或查询get session相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行finish相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：读取或查询get session orm相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(StudyTestSession).where(StudyTestSession.id == session_id, StudyTestSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_current_turn(self, db: AsyncSession, user_id: str, session_id: str, turn_index: int):
        """
        用途：读取或查询get current turn相关的数据或流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - session_id（str）：调用方传入的session_id数据或控制参数，用于驱动本函数处理流程。
        - turn_index（int）：调用方传入的turn_index数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        result = await db.execute(
            select(StudyTestTurn).where(
                StudyTestTurn.session_id == session_id,
                StudyTestTurn.user_id == user_id,
                StudyTestTurn.turn_index == turn_index,
            )
        )
        return result.scalar_one_or_none()

    async def _model_json(self, prompt: str) -> dict | None:
        """
        用途：异步执行model json相关业务流程。

        参数：
        - prompt（str）：调用方传入的prompt数据或控制参数，用于驱动本函数处理流程。

        返回：dict | None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await model_json(prompt)

    async def _generate_question(
        self,
        chunks: list[SourceChunk],
        difficulty: str,
        focus: str | None,
        turn_index: int,
        previous_question: str | None = None,
        previous_answer: str | None = None,
    ) -> str:
        """
        用途：生成generate question相关的数据或流程。

        参数：
        - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。
        - difficulty（str）：调用方传入的difficulty数据或控制参数，用于驱动本函数处理流程。
        - focus（str | None）：调用方传入的focus数据或控制参数，用于驱动本函数处理流程。
        - turn_index（int）：调用方传入的turn_index数据或控制参数，用于驱动本函数处理流程。
        - previous_question（str | None）：调用方传入的previous_question数据或控制参数，用于驱动本函数处理流程。
        - previous_answer（str | None）：调用方传入的previous_answer数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行evaluate answer相关业务流程。

        参数：
        - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。
        - question（str）：调用方传入的question数据或控制参数，用于驱动本函数处理流程。
        - answer（str）：调用方传入的answer数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：异步执行finish payload相关业务流程。

        参数：
        - db（AsyncSession）：调用方传入的db数据或控制参数，用于驱动本函数处理流程。
        - session（StudyTestSession）：调用方传入的session数据或控制参数，用于驱动本函数处理流程。
        - chunks（list[SourceChunk]）：调用方传入的chunks数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
