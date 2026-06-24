"""
模块职责：存储服务模块，负责本地/SFTP 文件读写、StorageObject 元数据和存储 URI 管理。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import asyncio
import hashlib
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

from db.db_config import AsyncSessionLocal
from mvc.models.storage_object import StorageObject
from utils.env_loader import require_env_declared


LOCAL_HOSTS = {"localhost", "127.0.0.1"}
BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_LOCAL_BASE_DIR = BACKEND_DIR / "data"


def _env(name: str) -> str:
    """
    用途：执行env相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return require_env_declared(name)


def _safe_segment(value: str) -> str:
    """
    用途：执行safe segment相关业务逻辑。

    参数：
    - value（str）：调用方传入的value数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._")
    return cleaned or "object"


def _file_ext(filename: str | None, fallback: str = ".bin") -> str:
    """
    用途：执行file ext相关业务逻辑。

    参数：
    - filename（str | None）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
    - fallback（str）：调用方传入的fallback数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    suffix = Path(filename or "").suffix.lower()
    return suffix or fallback


def _sha256(content: bytes) -> str:
    """
    用途：执行sha256相关业务逻辑。

    参数：
    - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class StorageSettings:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - host（str）：保存host相关状态、配置或数据字段。
    - protocol（str）：保存protocol相关状态、配置或数据字段。
    - port（int）：保存port相关状态、配置或数据字段。
    - username（str）：保存username相关状态、配置或数据字段。
    - password（str）：保存password相关状态、配置或数据字段。
    - base_dir（str）：保存base_dir相关状态、配置或数据字段。
    - uri_alias（str）：保存uri_alias相关状态、配置或数据字段。
    - backend（str）：保存backend相关状态、配置或数据字段。
    """
    host: str
    protocol: str
    port: int
    username: str
    password: str
    base_dir: str
    uri_alias: str
    backend: str

    @property
    def is_local(self) -> bool:
        """
        用途：执行is local相关业务逻辑。

        参数：无显式业务参数。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return self.host in LOCAL_HOSTS


def load_storage_settings() -> StorageSettings:
    """
    用途：加载load storage settings相关的数据或流程。

    参数：无显式业务参数。

    返回：StorageSettings；返回值供调用方继续编排业务流程或生成接口响应。
    """
    host = _env("FILE_STORAGE_HOST").lower() or "localhost"
    protocol = _env("FILE_STORAGE_PROTOCOL").lower() or "sftp"
    port = int(_env("FILE_STORAGE_PORT") or "22")
    username = _env("FILE_STORAGE_USERNAME")
    password = _env("FILE_STORAGE_PASSWORD")
    uri_alias = _env("FILE_STORAGE_URI_ALIAS") or "files"
    base_dir = _env("FILE_STORAGE_BASE_DIR")

    if host in LOCAL_HOSTS:
        base_dir = base_dir or str(DEFAULT_LOCAL_BASE_DIR)
        return StorageSettings(
            host=host,
            protocol="local",
            port=0,
            username="",
            password="",
            base_dir=str(Path(base_dir).resolve()),
            uri_alias=uri_alias,
            backend="local",
        )

    if protocol != "sftp":
        raise ValueError("FILE_STORAGE_PROTOCOL 首期仅支持 sftp")
    if not base_dir:
        raise ValueError("远程文件存储必须配置 FILE_STORAGE_BASE_DIR")
    if not username:
        raise ValueError("远程文件存储必须配置 FILE_STORAGE_USERNAME")
    if not password:
        raise ValueError("远程文件存储必须配置 FILE_STORAGE_PASSWORD")

    return StorageSettings(
        host=host,
        protocol=protocol,
        port=port,
        username=username,
        password=password,
        base_dir=base_dir.rstrip("/"),
        uri_alias=uri_alias,
        backend="sftp",
    )


class LocalStorageAdapter:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - settings（实例属性，由构造函数注入或初始化）：保存settings相关状态、配置或数据字段。
    - base_dir（实例属性，由构造函数注入或初始化）：保存base_dir相关状态、配置或数据字段。
    """
    def __init__(self, settings: StorageSettings):
        """
        用途：执行init相关业务逻辑。

        参数：
        - settings（StorageSettings）：调用方传入的settings数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.settings = settings
        self.base_dir = Path(settings.base_dir)

    def resolve_path(self, relative_path: str) -> str:
        """
        用途：解析并归一化resolve path相关的数据或流程。

        参数：
        - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        path = (self.base_dir / relative_path).resolve()
        base = self.base_dir.resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise ValueError("非法存储路径")
        return str(path)

    async def write_bytes(self, relative_path: str, content: bytes) -> str:
        """
        用途：异步执行write bytes相关业务流程。

        参数：
        - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。
        - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        path = self.resolve_path(relative_path)

        def _write() -> None:
            """
            用途：执行write相关业务逻辑。

            参数：无显式业务参数。

            返回：None；返回值供调用方继续编排业务流程或生成接口响应。
            """
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        await asyncio.to_thread(_write)
        return path

    async def read_bytes(self, storage_path: str) -> bytes:
        """
        用途：异步执行read bytes相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await asyncio.to_thread(Path(storage_path).read_bytes)

    async def delete(self, storage_path: str) -> None:
        """
        用途：异步执行delete相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        def _delete() -> None:
            """
            用途：执行delete相关业务逻辑。

            参数：无显式业务参数。

            返回：None；返回值供调用方继续编排业务流程或生成接口响应。
            """
            try:
                Path(storage_path).unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(_delete)

    async def exists(self, storage_path: str) -> bool:
        """
        用途：异步执行exists相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await asyncio.to_thread(Path(storage_path).exists)


class SftpStorageAdapter:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - settings（实例属性，由构造函数注入或初始化）：保存settings相关状态、配置或数据字段。
    """
    def __init__(self, settings: StorageSettings):
        """
        用途：执行init相关业务逻辑。

        参数：
        - settings（StorageSettings）：调用方传入的settings数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.settings = settings

    def resolve_path(self, relative_path: str) -> str:
        """
        用途：解析并归一化resolve path相关的数据或流程。

        参数：
        - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        return posixpath.join(self.settings.base_dir, relative_path.replace("\\", "/"))

    def _connect(self):
        """
        用途：执行connect相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        import paramiko

        transport = paramiko.Transport((self.settings.host, self.settings.port))
        transport.connect(username=self.settings.username, password=self.settings.password)
        return transport, paramiko.SFTPClient.from_transport(transport)

    @staticmethod
    def _mkdir_p(sftp, remote_dir: str) -> None:
        """
        用途：执行mkdir p相关业务逻辑。

        参数：
        - sftp（未显式标注）：调用方传入的sftp数据或控制参数，用于驱动本函数处理流程。
        - remote_dir（str）：调用方传入的remote_dir数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。
        """
        current = "/"
        for segment in [part for part in remote_dir.split("/") if part]:
            current = posixpath.join(current, segment)
            try:
                sftp.stat(current)
            except OSError:
                sftp.mkdir(current)

    async def write_bytes(self, relative_path: str, content: bytes) -> str:
        """
        用途：异步执行write bytes相关业务流程。

        参数：
        - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。
        - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        remote_path = self.resolve_path(relative_path)

        def _write() -> None:
            """
            用途：执行write相关业务逻辑。

            参数：无显式业务参数。

            返回：None；返回值供调用方继续编排业务流程或生成接口响应。
            """
            transport, sftp = self._connect()
            try:
                self._mkdir_p(sftp, posixpath.dirname(remote_path))
                with sftp.file(remote_path, "wb") as handle:
                    handle.write(content)
            finally:
                sftp.close()
                transport.close()

        await asyncio.to_thread(_write)
        return remote_path

    async def read_bytes(self, storage_path: str) -> bytes:
        """
        用途：异步执行read bytes相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        def _read() -> bytes:
            """
            用途：执行read相关业务逻辑。

            参数：无显式业务参数。

            返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。
            """
            transport, sftp = self._connect()
            try:
                with sftp.file(storage_path, "rb") as handle:
                    return handle.read()
            finally:
                sftp.close()
                transport.close()

        return await asyncio.to_thread(_read)

    async def delete(self, storage_path: str) -> None:
        """
        用途：异步执行delete相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        def _delete() -> None:
            """
            用途：执行delete相关业务逻辑。

            参数：无显式业务参数。

            返回：None；返回值供调用方继续编排业务流程或生成接口响应。
            """
            transport, sftp = self._connect()
            try:
                try:
                    sftp.remove(storage_path)
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
            finally:
                sftp.close()
                transport.close()

        await asyncio.to_thread(_delete)

    async def exists(self, storage_path: str) -> bool:
        """
        用途：异步执行exists相关业务流程。

        参数：
        - storage_path（str）：调用方传入的storage_path数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        def _exists() -> bool:
            """
            用途：执行exists相关业务逻辑。

            参数：无显式业务参数。

            返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
            """
            transport, sftp = self._connect()
            try:
                try:
                    sftp.stat(storage_path)
                    return True
                except OSError:
                    return False
            finally:
                sftp.close()
                transport.close()

        return await asyncio.to_thread(_exists)


class StorageService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - settings（实例属性，由构造函数注入或初始化）：保存settings相关状态、配置或数据字段。
    - adapter（实例属性，由构造函数注入或初始化）：保存adapter相关状态、配置或数据字段。
    """
    def __init__(self, settings: StorageSettings | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - settings（StorageSettings | None）：调用方传入的settings数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.settings = settings or load_storage_settings()
        self.adapter = LocalStorageAdapter(self.settings) if self.settings.is_local else SftpStorageAdapter(self.settings)

    def _relative_path(self, kind: str, user_id: str, object_id: str, filename: str | None) -> str:
        """
        用途：执行relative path相关业务逻辑。

        参数：
        - kind（str）：调用方传入的kind数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - object_id（str）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。
        - filename（str | None）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        kind_segment = _safe_segment(kind)
        user_segment = _safe_segment(user_id)
        object_segment = _safe_segment(object_id)
        suffix = ".md" if kind_segment == "notes" else _file_ext(filename)
        return f"{kind_segment}/{user_segment}/{object_segment}{suffix}"

    def _storage_uri(self, relative_path: str) -> str:
        """
        用途：执行storage uri相关业务逻辑。

        参数：
        - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。
        """
        if self.settings.is_local:
            return f"{self.settings.uri_alias}://{relative_path}"
        return f"sftp://{self.settings.uri_alias}/{relative_path}"

    async def upload_bytes(
        self,
        *,
        kind: str,
        user_id: str,
        object_id: str,
        filename: str | None,
        content: bytes,
        mime_type: str | None,
    ) -> StorageObject:
        """
        用途：上传upload bytes相关的数据或流程。

        参数：
        - kind（str）：调用方传入的kind数据或控制参数，用于驱动本函数处理流程。
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - object_id（str）：调用方传入的object_id数据或控制参数，用于驱动本函数处理流程。
        - filename（str | None）：调用方传入的filename数据或控制参数，用于驱动本函数处理流程。
        - content（bytes）：调用方传入的content数据或控制参数，用于驱动本函数处理流程。
        - mime_type（str | None）：调用方传入的mime_type数据或控制参数，用于驱动本函数处理流程。

        返回：StorageObject；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        relative_path = self._relative_path(kind, user_id, object_id, filename)
        storage_path = await self.adapter.write_bytes(relative_path, content)
        return StorageObject(
            id=object_id,
            backend=self.settings.backend,
            host=self.settings.host,
            protocol=None if self.settings.is_local else self.settings.protocol,
            storage_uri=self._storage_uri(relative_path),
            storage_path=storage_path,
            original_filename=filename,
            mime_type=mime_type,
            file_ext=Path(relative_path).suffix.lower(),
            checksum_sha256=_sha256(content),
            size_bytes=len(content),
            status="uploaded",
        )

    async def read_bytes(self, storage_object_id: str) -> bytes:
        """
        用途：异步执行read bytes相关业务流程。

        参数：
        - storage_object_id（str）：调用方传入的storage_object_id数据或控制参数，用于驱动本函数处理流程。

        返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                raise FileNotFoundError(storage_object_id)
            return await self.read_object_bytes(storage_object)

    async def read_text(self, storage_object_id: str) -> str:
        """
        用途：异步执行read text相关业务流程。

        参数：
        - storage_object_id（str）：调用方传入的storage_object_id数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return (await self.read_bytes(storage_object_id)).decode("utf-8")

    async def read_object_bytes(self, storage_object: StorageObject) -> bytes:
        """
        用途：异步执行read object bytes相关业务流程。

        参数：
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：bytes；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return await self.adapter.read_bytes(storage_object.storage_path)

    async def read_object_text(self, storage_object: StorageObject) -> str:
        """
        用途：异步执行read object text相关业务流程。

        参数：
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：str；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        return (await self.read_object_bytes(storage_object)).decode("utf-8")

    async def delete_object(self, storage_object_id: str) -> None:
        """
        用途：删除delete object相关的数据或流程。

        参数：
        - storage_object_id（str）：调用方传入的storage_object_id数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                return
            await self.delete_storage_object_data(storage_object)
            storage_object.status = "deleted"
            await session.commit()

    async def delete_storage_object_data(self, storage_object: StorageObject) -> None:
        """
        用途：删除delete storage object data相关的数据或流程。

        参数：
        - storage_object（StorageObject）：调用方传入的storage_object数据或控制参数，用于驱动本函数处理流程。

        返回：None；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        await self.adapter.delete(storage_object.storage_path)

    async def exists(self, storage_object_id: str) -> bool:
        """
        用途：异步执行exists相关业务流程。

        参数：
        - storage_object_id（str）：调用方传入的storage_object_id数据或控制参数，用于驱动本函数处理流程。

        返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                return False
            return await self.adapter.exists(storage_object.storage_path)


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """
    用途：读取或查询get storage service相关的数据或流程。

    参数：无显式业务参数。

    返回：StorageService；返回值供调用方继续编排业务流程或生成接口响应。
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
