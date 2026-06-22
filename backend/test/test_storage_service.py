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


def _env_keys(path: Path) -> set[str]:
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
    assert FILE_STORAGE_KEYS <= _env_keys(REPO_ROOT / relative_path)


def test_localhost_uses_local_adapter_and_default_backend_data(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_HOST", "localhost")
    monkeypatch.delenv("FILE_STORAGE_BASE_DIR", raising=False)
    monkeypatch.setenv("FILE_STORAGE_PROTOCOL", "sftp")
    monkeypatch.setenv("FILE_STORAGE_PORT", "2222")
    monkeypatch.setenv("FILE_STORAGE_USERNAME", "ignored")
    monkeypatch.setenv("FILE_STORAGE_PASSWORD", "ignored")

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
    monkeypatch.setenv("FILE_STORAGE_HOST", "127.0.0.1")
    monkeypatch.setenv("FILE_STORAGE_BASE_DIR", str(tmp_path))

    settings = load_storage_settings()

    assert settings.backend == "local"
    assert Path(settings.base_dir) == tmp_path.resolve()


def test_remote_sftp_uses_sftp_adapter(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_HOST", "db.example.internal")
    monkeypatch.setenv("FILE_STORAGE_PROTOCOL", "sftp")
    monkeypatch.setenv("FILE_STORAGE_PORT", "2200")
    monkeypatch.setenv("FILE_STORAGE_USERNAME", "ragfiles")
    monkeypatch.setenv("FILE_STORAGE_PASSWORD", "secret")
    monkeypatch.setenv("FILE_STORAGE_BASE_DIR", "/srv/ragnotebook/files")

    settings = load_storage_settings()
    service = StorageService(settings)

    assert settings.backend == "sftp"
    assert settings.port == 2200
    assert isinstance(service.adapter, SftpStorageAdapter)


def test_remote_storage_requires_base_dir(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_HOST", "db.example.internal")
    monkeypatch.setenv("FILE_STORAGE_PROTOCOL", "sftp")
    monkeypatch.setenv("FILE_STORAGE_USERNAME", "ragfiles")
    monkeypatch.setenv("FILE_STORAGE_PASSWORD", "secret")
    monkeypatch.delenv("FILE_STORAGE_BASE_DIR", raising=False)

    with pytest.raises(ValueError, match="FILE_STORAGE_BASE_DIR"):
        load_storage_settings()
