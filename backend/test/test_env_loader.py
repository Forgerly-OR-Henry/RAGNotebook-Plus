import os
from pathlib import Path

from utils.env_loader import backend_env_file, config_env_file, load_backend_env


def test_backend_env_path_is_separate_from_global_config(tmp_path: Path):
    backend_dir = tmp_path / "backend"
    config_dir = tmp_path / "config"
    backend_dir.mkdir()
    config_dir.mkdir()
    (backend_dir / ".env").write_text("BACKEND_PORT=10001\n", encoding="utf-8")
    (config_dir / ".env").write_text("BACKEND_PORT=10000\n", encoding="utf-8")

    assert config_env_file(backend_dir) == config_dir / ".env"
    assert backend_env_file(backend_dir) == backend_dir / ".env"


def test_manual_backend_load_reads_backend_env_only(tmp_path: Path, monkeypatch):
    backend_dir = tmp_path / "backend"
    config_dir = tmp_path / "config"
    backend_dir.mkdir()
    config_dir.mkdir()
    (backend_dir / ".env").write_text("BACKEND_PORT=10001\n", encoding="utf-8")
    (config_dir / ".env").write_text("BACKEND_PORT=10000\n", encoding="utf-8")

    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.delenv("RAGNOTEBOOK_ENV_INJECTED", raising=False)

    assert load_backend_env(backend_dir) is True
    assert os.environ["BACKEND_PORT"] == "10001"


def test_injected_env_skips_backend_env(tmp_path: Path, monkeypatch):
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text("BACKEND_PORT=10001\n", encoding="utf-8")

    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.setenv("RAGNOTEBOOK_ENV_INJECTED", "1")

    assert load_backend_env(backend_dir) is False
    assert "BACKEND_PORT" not in os.environ
