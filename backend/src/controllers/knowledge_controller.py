import os

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.routing import APIRouter

from core.rate_limit import rate_limit
from core.success_response import success_response
from db.db_config import get_db
from services.knowledge_service import KnowledgeService, get_knowledge_service
from schemas import (
    DocumentChunksResponse,
    KnowledgeDocumentDetail,
    KnowledgeListResponse,
    MD5ListResponse,
    MD5Record,
)
from utils.auth_utils import get_current_user_id
from utils.image_extractor import get_image_storage_dir

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


@knowledge_router.get("/documents/{document_id}", response_model=KnowledgeDocumentDetail)
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


@knowledge_router.get("/image/{md5}/{filename}")
async def serve_knowledge_image(
    md5: str,
    filename: str,
    user_id: str = Depends(get_current_user_id),
):
    image_dir = get_image_storage_dir(user_id, md5)
    image_path = os.path.abspath(os.path.join(image_dir, filename))
    allowed_dir = os.path.abspath(image_dir)
    if not image_path.startswith(allowed_dir):
        raise HTTPException(status_code=403, detail="非法路径")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    ext = os.path.splitext(filename)[1].lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    return FileResponse(image_path, media_type=media_type)


@knowledge_router.get("/images/all/{md5}")
async def serve_batch_images(
    md5: str,
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    return success_response(data=await knowledge_service.get_batch_images(user_id, md5))


# Deprecated compatibility endpoints. New clients must use /knowledge/documents.
@knowledge_router.post("/add/multiple/stream", deprecated=True)
async def add_vector_multiple_stream(
    files: list[UploadFile] = File(..., description="Deprecated: use /knowledge/documents"),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=3, window=60)),
):
    return await upload_documents(files, user_id, knowledge_service, _)


@knowledge_router.post("/add/single", deprecated=True)
async def add_vector_single(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=5, window=60)),
):
    return await upload_documents([file], user_id, knowledge_service, _)


@knowledge_router.post("/add/multiple", deprecated=True)
async def add_vector_multiple(
    files: list[UploadFile] = File(...),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=3, window=60)),
):
    return await upload_documents(files, user_id, knowledge_service, _)


@knowledge_router.get("/list", response_model=KnowledgeListResponse, deprecated=True)
async def get_user_knowledge_list(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    return await list_documents(db, user_id, knowledge_service, _)


@knowledge_router.get("/detail", response_model=KnowledgeDocumentDetail, deprecated=True)
async def get_document_detail_by_query(
    filename: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    documents = await knowledge_service.list_documents(db, user_id)
    match = next((doc for doc in documents if doc["id"] == filename or doc["filename"] == filename or doc["original_filename"] == filename), None)
    if not match:
        raise HTTPException(status_code=404, detail="文档不存在")
    return await get_document_detail(match["id"], db, user_id, knowledge_service, _)


@knowledge_router.get("/chunks", response_model=DocumentChunksResponse, deprecated=True)
async def get_document_chunks_by_query(
    filename: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    documents = await knowledge_service.list_documents(db, user_id)
    match = next((doc for doc in documents if doc["id"] == filename or doc["filename"] == filename or doc["original_filename"] == filename), None)
    if not match:
        raise HTTPException(status_code=404, detail="文档不存在")
    return await get_document_chunks(match["id"], db, user_id, knowledge_service, _)


@knowledge_router.delete("/clean", deprecated=True)
async def clean_user_vectors(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    return await clean_documents(db, user_id, knowledge_service)


@knowledge_router.delete("/delete/filename", deprecated=True)
async def delete_by_filename(
    filename: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    deleted = await knowledge_service.delete_by_filename(db, user_id, filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return success_response(data=None, message="文档已删除")


@knowledge_router.get("/md5/list", response_model=MD5ListResponse, deprecated=True)
async def get_all_md5_records(
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    records = await knowledge_service.list_md5_records(db, user_id)
    return success_response(data=MD5ListResponse(records=records, total_count=len(records)))


@knowledge_router.get("/md5/{md5_value}", response_model=MD5Record, deprecated=True)
async def get_md5_info(
    md5_value: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    _: None = Depends(rate_limit(limit=10, window=60)),
):
    md5_info = await knowledge_service.get_document_by_md5(db, user_id, md5_value)
    if not md5_info:
        raise HTTPException(status_code=404, detail="MD5记录不存在")
    return success_response(data=MD5Record(md5=md5_info["md5"], filename=md5_info["filename"], original_filename=md5_info["original_filename"], upload_time=md5_info["created_at"]))


@knowledge_router.delete("/md5/delete/{md5_value}", deprecated=True)
async def delete_single_md5(
    md5_value: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    documents = await knowledge_service.list_documents(db, user_id)
    match = next((doc for doc in documents if doc["md5"] == md5_value), None)
    if not match:
        raise HTTPException(status_code=404, detail="MD5记录不存在")
    await knowledge_service.delete_document(db, user_id, match["id"])
    return success_response(data=None, message="MD5记录和对应文档已删除")
