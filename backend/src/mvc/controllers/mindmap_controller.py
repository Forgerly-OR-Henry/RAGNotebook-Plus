from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from mvc.schemas import MindMapGenerateRequest, MindMapResponse, MindMapUpdateRequest
from mvc.services.mindmap_service import MindMapService
from utils.auth_utils import get_current_user_id

mindmap_router = APIRouter(prefix="/mindmaps", tags=["mindmaps"])


def get_mindmap_service() -> MindMapService:
    return MindMapService()


@mindmap_router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(
    payload: MindMapGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    try:
        data = await service.generate(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(data=MindMapResponse(**data))


@mindmap_router.get("/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(
    mindmap_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    data = await service.get(db, user_id, mindmap_id)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data=MindMapResponse(**data))


@mindmap_router.put("/{mindmap_id}", response_model=MindMapResponse)
async def update_mindmap(
    mindmap_id: str,
    payload: MindMapUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    data = await service.update(db, user_id, mindmap_id, payload)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data=MindMapResponse(**data))


@mindmap_router.get("/{mindmap_id}/export")
async def export_mindmap(
    mindmap_id: str,
    format: str = Query("json", pattern="^(json|mermaid)$"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: MindMapService = Depends(get_mindmap_service),
):
    data = await service.export(db, user_id, mindmap_id, format)
    if data is None:
        raise HTTPException(status_code=404, detail="思维导图不存在")
    return success_response(data={"format": format, "content": data})
