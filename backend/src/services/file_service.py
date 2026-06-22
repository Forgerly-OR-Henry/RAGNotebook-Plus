import os

from fastapi import HTTPException, UploadFile
from shortuuid import uuid as short_uuid

from core.logger_handler import logger
from repositories.runtime_store import delete_cache
from repositories.user_repository import UserRepository, user_repository
from utils.path_tool import get_media_path


class FileService:
    def __init__(self, user_repo: UserRepository | None = None):
        self.user_repo = user_repo or user_repository
        self._media_dir: str | None = None

    def _get_media_dir(self) -> str:
        if self._media_dir is None:
            self._media_dir = get_media_path()
        os.makedirs(os.path.join(self._media_dir, "img"), exist_ok=True)
        return self._media_dir

    async def upload_avatar(self, file: UploadFile, user_id: str) -> dict:
        media_dir = self._get_media_dir()
        filename = short_uuid() + os.path.splitext(file.filename or ".bin")[1]
        filepath = os.path.join(media_dir, "img", filename)

        try:
            content = await file.read()
            with open(filepath, "wb") as handle:
                handle.write(content)
        except Exception as exc:
            logger.error(f"文件上传失败: {exc}")
            raise HTTPException(status_code=500, detail="图片上传失败") from exc

        file_url = f"/media/img/{filename}"
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
