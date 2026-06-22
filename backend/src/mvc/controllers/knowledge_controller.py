from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from mvc.schemas import DocumentChunksResponse, DocumentDetailResponse, KnowledgeListResponse
from mvc.services.knowledge_service import KnowledgeService, get_knowledge_service
from utils.auth_utils import get_current_user_id

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@knowledge_router.post("/documents")
async def upload_documents(
    files: list[UploadFile] = File(..., description="要上传的文件列表，支持 PDF、TXT、Markdown、Word、PPT"),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=3, window=60)),
):
    return StreamingResponse(
        knowledge_service.upload_stream(files, user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@knowledge_router.get("/documents", response_model=KnowledgeListResponse)
async def list_documents(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    documents = await knowledge_service.list_documents(db, user_id)
    return success_response(data=KnowledgeListResponse(documents=documents, total_count=len(documents)))


@knowledge_router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    document = await knowledge_service.get_document_detail(db, user_id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(data=document)


@knowledge_router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    chunks = await knowledge_service.get_document_chunks(db, user_id, document_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(data=chunks)


@knowledge_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    deleted = await knowledge_service.delete_document(db, user_id, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(data=None, message="文档已删除")


@knowledge_router.delete("/documents")
async def clean_documents(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    await knowledge_service.clean_user_documents(db, user_id)
    return success_response(data=None, message="知识库已清空")
