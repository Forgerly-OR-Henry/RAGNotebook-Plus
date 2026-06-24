import os

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from shortuuid import uuid as short_uuid

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.models.storage_object import StorageObject
from mvc.repositories.runtime_store import delete_cache
from mvc.repositories.user_repository import UserRepository, user_repository
from mvc.services.storage_service import StorageService, get_storage_service

MAX_AVATAR_BYTES = 5 * 1024 * 1024


class FileService:
    def __init__(self, user_repo: UserRepository | None = None, storage_service: StorageService | None = None):
        self.user_repo = user_repo or user_repository
        self.storage_service = storage_service or get_storage_service()

    async def upload_avatar(self, file: UploadFile, user_id: str) -> dict:
        if file.content_type and not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="请选择图片文件")

        object_id = short_uuid()
        filename = object_id + os.path.splitext(file.filename or ".bin")[1]
        content = await file.read()
        if len(content) > MAX_AVATAR_BYTES:
            raise HTTPException(status_code=400, detail="头像图片不能超过 5MB")

        try:
            storage_object = await self.storage_service.upload_bytes(
                kind="avatars",
                user_id=user_id,
                object_id=object_id,
                filename=filename,
                content=content,
                mime_type=file.content_type,
            )
            async with AsyncSessionLocal() as session:
                session.add(storage_object)
                await session.commit()
        except Exception as exc:
            if "storage_object" in locals():
                await self.storage_service.delete_storage_object_data(storage_object)
            logger.error(f"文件上传失败: {exc}")
            raise HTTPException(status_code=500, detail="图片上传失败") from exc

        file_url = self.public_avatar_url(storage_object.id)
        await self.user_repo.update_avatar(user_id, file_url)
        await delete_cache(f"user:{user_id}")
        return {
            "success": True,
            "data": {
                "url": file_url,
                "alt": "当前加载较为缓慢，请稍后重试",
                "href": file_url,
            },
        }

    @staticmethod
    def public_avatar_url(object_id: str) -> str:
        return f"/file/avatar/{object_id}"

    async def get_avatar_response(self, object_id: str) -> Response:
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, object_id)
            if not storage_object or not self._is_avatar_object(storage_object):
                raise HTTPException(status_code=404, detail="头像不存在")

        content = await self.storage_service.read_object_bytes(storage_object)
        return Response(content=content, media_type=storage_object.mime_type or "application/octet-stream")

    @staticmethod
    def _is_avatar_object(storage_object: StorageObject) -> bool:
        return "://avatars/" in storage_object.storage_uri


_file_service = FileService()


def get_file_service() -> FileService:
    return _file_service
