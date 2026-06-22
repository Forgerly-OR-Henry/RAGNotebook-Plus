import os

from fastapi import HTTPException, UploadFile
from shortuuid import uuid as short_uuid

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from mvc.repositories.runtime_store import delete_cache
from mvc.repositories.user_repository import UserRepository, user_repository
from mvc.services.storage_service import StorageService, get_storage_service


class FileService:
    def __init__(self, user_repo: UserRepository | None = None, storage_service: StorageService | None = None):
        self.user_repo = user_repo or user_repository
        self.storage_service = storage_service or get_storage_service()

    async def upload_avatar(self, file: UploadFile, user_id: str) -> dict:
        object_id = short_uuid()
        filename = object_id + os.path.splitext(file.filename or ".bin")[1]

        try:
            content = await file.read()
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

        file_url = storage_object.storage_uri
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


_file_service = FileService()


def get_file_service() -> FileService:
    return _file_service
