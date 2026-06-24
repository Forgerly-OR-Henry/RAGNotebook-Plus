"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

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
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - user_repo（实例属性，由构造函数注入或初始化）：保存user_repo相关状态、配置或数据字段。
    - storage_service（实例属性，由构造函数注入或初始化）：保存storage_service相关状态、配置或数据字段。
    """
    def __init__(self, user_repo: UserRepository | None = None, storage_service: StorageService | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - user_repo（UserRepository | None）：调用方传入的user_repo数据或控制参数，用于驱动本函数处理流程。
        - storage_service（StorageService | None）：调用方传入的storage_service数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.user_repo = user_repo or user_repository
        self.storage_service = storage_service or get_storage_service()

    async def upload_avatar(self, file: UploadFile, user_id: str) -> dict:
        """
        用途：上传upload avatar相关的数据或流程。

        参数：
        - file（UploadFile）：调用方传入的file数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

        返回：dict；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
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
        """
        用途：执行public avatar url相关业务逻辑。

        参数：
        - object_id（str）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return f"/file/avatar/{object_id}"

    async def get_avatar_response(self, object_id: str) -> Response:
        """
        用途：读取或查询get avatar response相关的数据或流程。

        参数：
        - object_id（str）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。

        返回：Response；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, object_id)
            if not storage_object or not self._is_avatar_object(storage_object):
                raise HTTPException(status_code=404, detail="头像不存在")

        content = await self.storage_service.read_object_bytes(storage_object)
        return Response(content=content, media_type=storage_object.mime_type or "application/octet-stream")

    @staticmethod
    def _is_avatar_object(storage_object: StorageObject) -> bool:
        """
        用途：执行is avatar object相关业务逻辑。

        参数：
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return "://avatars/" in storage_object.storage_uri


_file_service = FileService()


def get_file_service() -> FileService:
    """
    用途：读取或查询get file service相关的数据或流程。

    参数：无显式业务参数。

    返回：FileService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return _file_service
