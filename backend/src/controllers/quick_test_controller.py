from fastapi import Depends, HTTPException
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from schemas import (
    QuickTestAnswerRequest,
    QuickTestAnswerResponse,
    QuickTestCreateRequest,
    QuickTestFinishResponse,
    QuickTestSessionResponse,
    QuickTestStartResponse,
)
from services.quick_test_service import QuickTestService
from utils.auth_utils import get_current_user_id

quick_test_router = APIRouter(prefix="/quick-test", tags=["quick-test"])


def get_quick_test_service() -> QuickTestService:
    return QuickTestService()


@quick_test_router.post("/sessions", response_model=QuickTestStartResponse)
async def create_quick_test_session(
    payload: QuickTestCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    try:
        data = await service.create_session(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=QuickTestStartResponse(**data))


@quick_test_router.post("/sessions/{session_id}/answer", response_model=QuickTestAnswerResponse)
async def answer_quick_test(
    session_id: str,
    payload: QuickTestAnswerRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
    _: None = Depends(rate_limit(limit=20, window=60)),
):
    data = await service.answer(db, user_id, session_id, payload.answer)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestAnswerResponse(**data))


@quick_test_router.get("/sessions/{session_id}", response_model=QuickTestSessionResponse)
async def get_quick_test_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
):
    data = await service.get_session(db, user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestSessionResponse(**data))


@quick_test_router.post("/sessions/{session_id}/finish", response_model=QuickTestFinishResponse)
async def finish_quick_test_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: QuickTestService = Depends(get_quick_test_service),
):
    data = await service.finish(db, user_id, session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="快速测试会话不存在")
    return success_response(data=QuickTestFinishResponse(**data))
