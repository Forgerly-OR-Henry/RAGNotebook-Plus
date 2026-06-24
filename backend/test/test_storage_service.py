"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from pathlib import Path

import pytest

from mvc.services import storage_service as storage_module
from mvc.services.storage_service import LocalStorageAdapter, SftpStorageAdapter, StorageService, load_storage_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
FILE_STORAGE_KEYS = {
    "FILE_STORAGE_HOST",
    "FILE_STORAGE_PROTOCOL",
    "FILE_STORAGE_PORT",
    "FILE_STORAGE_USERNAME",
    "FILE_STORAGE_PASSWORD",
    "FILE_STORAGE_BASE_DIR",
    "FILE_STORAGE_URI_ALIAS",
}


def _set_storage_env(monkeypatch, **overrides):
    """
    用途：执行set storage env相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。
    - overrides（未显式标注）：调用方传入的overrides数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    values = {
        "FILE_STORAGE_HOST": "localhost",
        "FILE_STORAGE_PROTOCOL": "sftp",
        "FILE_STORAGE_PORT": "22",
        "FILE_STORAGE_USERNAME": "",
        "FILE_STORAGE_PASSWORD": "",
        "FILE_STORAGE_BASE_DIR": "",
        "FILE_STORAGE_URI_ALIAS": "files",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def _env_keys(path: Path) -> set[str]:
    """
    用途：执行env keys相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

    返回：set[str]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    keys = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


@pytest.mark.parametrize(
    "relative_path",
    ["config/.env.example", "backend/.env.example"],
)
def test_file_storage_keys_are_declared_in_env_templates(relative_path):
    """
    用途：执行test file storage keys are declared in env templates相关业务逻辑。

    参数：
    - relative_path（未显式标注）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert FILE_STORAGE_KEYS <= _env_keys(REPO_ROOT / relative_path)


def test_localhost_uses_local_adapter_and_default_backend_data(monkeypatch):
    """
    用途：执行test localhost uses local adapter and default backend data相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(
        monkeypatch,
        FILE_STORAGE_HOST="localhost",
        FILE_STORAGE_PORT="2222",
        FILE_STORAGE_USERNAME="ignored",
        FILE_STORAGE_PASSWORD="ignored",
        FILE_STORAGE_BASE_DIR="",
    )

    settings = load_storage_settings()
    service = StorageService(settings)

    assert settings.backend == "local"
    assert settings.protocol == "local"
    assert settings.port == 0
    assert settings.username == ""
    assert settings.password == ""
    assert Path(settings.base_dir) == storage_module.DEFAULT_LOCAL_BASE_DIR.resolve()
    assert isinstance(service.adapter, LocalStorageAdapter)


def test_loopback_uses_configured_local_directory(monkeypatch, tmp_path):
    """
    用途：执行test loopback uses configured local directory相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。
    - tmp_path（未显式标注）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(monkeypatch, FILE_STORAGE_HOST="127.0.0.1", FILE_STORAGE_BASE_DIR=str(tmp_path))

    settings = load_storage_settings()

    assert settings.backend == "local"
    assert Path(settings.base_dir) == tmp_path.resolve()


def test_local_storage_rejects_prefix_path_escape(monkeypatch, tmp_path):
    """
    用途：执行test local storage rejects prefix path escape相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。
    - tmp_path（未显式标注）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(monkeypatch)
    settings = load_storage_settings()
    settings = storage_module.StorageSettings(
        host=settings.host,
        protocol=settings.protocol,
        port=settings.port,
        username=settings.username,
        password=settings.password,
        base_dir=str(tmp_path / "base"),
        uri_alias=settings.uri_alias,
        backend=settings.backend,
    )
    adapter = LocalStorageAdapter(settings)

    with pytest.raises(ValueError, match="非法存储路径"):
        adapter.resolve_path("../base_evil/file.txt")


def test_remote_sftp_uses_sftp_adapter(monkeypatch):
    """
    用途：执行test remote sftp uses sftp adapter相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(
        monkeypatch,
        FILE_STORAGE_HOST="db.example.internal",
        FILE_STORAGE_PORT="2200",
        FILE_STORAGE_USERNAME="ragfiles",
        FILE_STORAGE_PASSWORD="secret",
        FILE_STORAGE_BASE_DIR="/srv/ragnotebook/files",
    )

    settings = load_storage_settings()
    service = StorageService(settings)

    assert settings.backend == "sftp"
    assert settings.port == 2200
    assert isinstance(service.adapter, SftpStorageAdapter)


def test_remote_storage_requires_base_dir(monkeypatch):
    """
    用途：执行test remote storage requires base dir相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(
        monkeypatch,
        FILE_STORAGE_HOST="db.example.internal",
        FILE_STORAGE_USERNAME="ragfiles",
        FILE_STORAGE_PASSWORD="secret",
        FILE_STORAGE_BASE_DIR="",
    )

    with pytest.raises(ValueError, match="FILE_STORAGE_BASE_DIR"):
        load_storage_settings()


def test_storage_settings_requires_declared_fields(monkeypatch):
    """
    用途：执行test storage settings requires declared fields相关业务逻辑。

    参数：
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    _set_storage_env(monkeypatch)
    monkeypatch.delenv("FILE_STORAGE_HOST", raising=False)

    with pytest.raises(RuntimeError, match="FILE_STORAGE_HOST"):
        load_storage_settings()
