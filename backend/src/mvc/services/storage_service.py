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
    return require_env_declared(name)


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._")
    return cleaned or "object"


def _file_ext(filename: str | None, fallback: str = ".bin") -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix or fallback


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class StorageSettings:
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
        return self.host in LOCAL_HOSTS


def load_storage_settings() -> StorageSettings:
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
    def __init__(self, settings: StorageSettings):
        self.settings = settings
        self.base_dir = Path(settings.base_dir)

    def resolve_path(self, relative_path: str) -> str:
        path = (self.base_dir / relative_path).resolve()
        base = self.base_dir.resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise ValueError("非法存储路径")
        return str(path)

    async def write_bytes(self, relative_path: str, content: bytes) -> str:
        path = self.resolve_path(relative_path)

        def _write() -> None:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        await asyncio.to_thread(_write)
        return path

    async def read_bytes(self, storage_path: str) -> bytes:
        return await asyncio.to_thread(Path(storage_path).read_bytes)

    async def delete(self, storage_path: str) -> None:
        def _delete() -> None:
            try:
                Path(storage_path).unlink()
            except FileNotFoundError:
                pass

        await asyncio.to_thread(_delete)

    async def exists(self, storage_path: str) -> bool:
        return await asyncio.to_thread(Path(storage_path).exists)


class SftpStorageAdapter:
    def __init__(self, settings: StorageSettings):
        self.settings = settings

    def resolve_path(self, relative_path: str) -> str:
        return posixpath.join(self.settings.base_dir, relative_path.replace("\\", "/"))

    def _connect(self):
        import paramiko

        transport = paramiko.Transport((self.settings.host, self.settings.port))
        transport.connect(username=self.settings.username, password=self.settings.password)
        return transport, paramiko.SFTPClient.from_transport(transport)

    @staticmethod
    def _mkdir_p(sftp, remote_dir: str) -> None:
        current = "/"
        for segment in [part for part in remote_dir.split("/") if part]:
            current = posixpath.join(current, segment)
            try:
                sftp.stat(current)
            except OSError:
                sftp.mkdir(current)

    async def write_bytes(self, relative_path: str, content: bytes) -> str:
        remote_path = self.resolve_path(relative_path)

        def _write() -> None:
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
        def _read() -> bytes:
            transport, sftp = self._connect()
            try:
                with sftp.file(storage_path, "rb") as handle:
                    return handle.read()
            finally:
                sftp.close()
                transport.close()

        return await asyncio.to_thread(_read)

    async def delete(self, storage_path: str) -> None:
        def _delete() -> None:
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
        def _exists() -> bool:
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
    def __init__(self, settings: StorageSettings | None = None):
        self.settings = settings or load_storage_settings()
        self.adapter = LocalStorageAdapter(self.settings) if self.settings.is_local else SftpStorageAdapter(self.settings)

    def _relative_path(self, kind: str, user_id: str, object_id: str, filename: str | None) -> str:
        kind_segment = _safe_segment(kind)
        user_segment = _safe_segment(user_id)
        object_segment = _safe_segment(object_id)
        suffix = ".md" if kind_segment == "notes" else _file_ext(filename)
        return f"{kind_segment}/{user_segment}/{object_segment}{suffix}"

    def _storage_uri(self, relative_path: str) -> str:
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
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                raise FileNotFoundError(storage_object_id)
            return await self.read_object_bytes(storage_object)

    async def read_text(self, storage_object_id: str) -> str:
        return (await self.read_bytes(storage_object_id)).decode("utf-8")

    async def read_object_bytes(self, storage_object: StorageObject) -> bytes:
        return await self.adapter.read_bytes(storage_object.storage_path)

    async def read_object_text(self, storage_object: StorageObject) -> str:
        return (await self.read_object_bytes(storage_object)).decode("utf-8")

    async def delete_object(self, storage_object_id: str) -> None:
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                return
            await self.delete_storage_object_data(storage_object)
            storage_object.status = "deleted"
            await session.commit()

    async def delete_storage_object_data(self, storage_object: StorageObject) -> None:
        await self.adapter.delete(storage_object.storage_path)

    async def exists(self, storage_object_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            storage_object = await session.get(StorageObject, storage_object_id)
            if storage_object is None:
                return False
            return await self.adapter.exists(storage_object.storage_path)


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
