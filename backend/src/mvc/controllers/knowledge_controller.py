import re
from urllib.parse import quote

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from fastapi.routing import APIRouter

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from mvc.schemas import (
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentResponse,
    KnowledgeBatchCategoryRequest,
    KnowledgeBatchFolderRequest,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderResponse,
    KnowledgeFolderTreeResponse,
    KnowledgeFolderUpdate,
    KnowledgeListResponse,
)
from mvc.services.knowledge_service import KnowledgeService, get_knowledge_service
from mvc.services.knowledge_service import KnowledgeFolderError
from utils.auth_utils import get_current_user_id

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@knowledge_router.post("/documents")
async def upload_documents(
    files: list[UploadFile] = File(..., description="要上传的文件列表，支持 PDF、TXT、Markdown、Word、PPT"),
    user_id: str = Depends(get_current_user_id),
    folder_id: str = Form(None),
    category: str = Form(None),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=3, window=60)),
):
    return StreamingResponse(
        knowledge_service.upload_stream(files, user_id, folder_id=folder_id, category=category),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@knowledge_router.get("/documents", response_model=KnowledgeListResponse)
async def list_documents(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    folder_id: str = Query(None),
    unfiled: bool = Query(False),
    category: str = Query(None),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    try:
        documents = await knowledge_service.list_documents(
            db=db,
            user_id=user_id,
            folder_id=folder_id,
            unfiled=unfiled,
            category=category,
        )
    except KnowledgeFolderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


@knowledge_router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    payload = await knowledge_service.get_document_file(db, user_id, document_id)
    if not payload:
        raise HTTPException(status_code=404, detail="文档不存在")

    document, storage_object, content = payload
    fallback = f"{document.id}{document.file_ext or ''}"
    filename = storage_object.original_filename or document.title or fallback
    safe_filename = re.sub(r'[\\/:*?"<>|]', "_", filename).strip() or fallback
    return Response(
        content=content,
        media_type=document.mime_type or storage_object.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(safe_filename, safe='')}",
            "X-Content-Type-Options": "nosniff",
        },
    )


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


@knowledge_router.put("/documents/{document_id}/metadata", response_model=DocumentResponse)
async def update_document_metadata(
    document_id: str,
    payload: KnowledgeDocumentMetadataUpdate,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    document = await knowledge_service.update_document_metadata(db, user_id, document_id, payload)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(message="文档信息已更新", data=document)


@knowledge_router.post("/documents/{document_id}/auto-tag", response_model=DocumentResponse)
async def auto_tag_document(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    document = await knowledge_service.auto_tag_document(db, user_id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(message="AI 识别完成", data=document)


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


@knowledge_router.get("/stats")
async def get_knowledge_stats(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    data = await knowledge_service.get_category_stats(db, user_id)
    return success_response(data=data)


@knowledge_router.delete("/category/{category}")
async def delete_knowledge_category(
    category: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    deleted = await knowledge_service.delete_category(db, user_id, category)
    return success_response(data={"deleted_count": deleted}, message=f"成功删除分类「{category}」及其 {deleted} 篇文档")


@knowledge_router.get("/folders")
async def list_knowledge_folders(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    data = await knowledge_service.list_folders(db, user_id)
    return success_response(data=data)


@knowledge_router.post("/folders")
async def create_knowledge_folder(
    payload: KnowledgeFolderCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        folder = await knowledge_service.create_folder(db, user_id, payload)
    except KnowledgeFolderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(message="文件夹创建成功", data=folder)


@knowledge_router.put("/folders/{folder_id}")
async def update_knowledge_folder(
    folder_id: str,
    payload: KnowledgeFolderUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        folder = await knowledge_service.update_folder(db, user_id, folder_id, payload)
    except KnowledgeFolderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not folder:
        return success_response(message="文件夹不存在")
    return success_response(message="文件夹更新成功", data=folder)


@knowledge_router.delete("/folders/{folder_id}")
async def delete_knowledge_folder(
    folder_id: str,
    mode: str = Query("unfile", pattern="^(unfile|delete_documents)$"),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        deleted = await knowledge_service.delete_folder(db, user_id, folder_id, mode)
    except KnowledgeFolderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if deleted is None:
        return success_response(message="文件夹不存在")
    if mode == "delete_documents":
        return success_response(message=f"文件夹已删除，并删除 {deleted} 篇文档")
    return success_response(message="文件夹已删除，文档已移回未归档")


@knowledge_router.put("/batch/folder")
async def batch_update_knowledge_folder(
    payload: KnowledgeBatchFolderRequest,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        updated = await knowledge_service.batch_update_folder(db, user_id, payload)
    except KnowledgeFolderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(message=f"成功移动 {updated} 篇文档")


@knowledge_router.put("/batch/category")
async def batch_update_knowledge_category(
    payload: KnowledgeBatchCategoryRequest,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    updated = await knowledge_service.batch_update_category(db, user_id, payload)
    return success_response(message=f"成功更新 {updated} 篇文档的分类")
