from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRouter
from sqlalchemy import select

from db.db_config import get_db
from mvc.models.document import Document
from mvc.models.storage_object import StorageObject
from mvc.services.storage_service import StorageService, get_storage_service
from utils.auth_utils import get_current_user_id

document_router = APIRouter(prefix="/documents", tags=["documents"])


@document_router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    db=Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    storage_service: StorageService = Depends(get_storage_service),
):
    result = await db.execute(
        select(Document, StorageObject)
        .join(StorageObject, Document.storage_object_id == StorageObject.id)
        .where(Document.id == document_id, Document.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")

    document, storage_object = row
    content = await storage_service.read_object_bytes(storage_object)
    fallback = f"{document.id}{document.file_ext or ''}"
    filename = storage_object.original_filename or document.title or fallback
    safe_filename = re.sub(r'[\\/:*?"<>|]', "_", filename).strip() or fallback
    return Response(
        content=content,
        media_type=document.mime_type or storage_object.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(safe_filename, safe='')}",
        },
    )
