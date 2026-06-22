from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


INJECTED_ENV_FLAG = "RAGNOTEBOOK_ENV_INJECTED"
FILE_BACKED_SECRET_KEYS = ("ALIYUN_ACCESS_KEY_SECRET",)


def is_env_injected() -> bool:
    return os.getenv(INJECTED_ENV_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def config_env_file(backend_dir: str | Path | None = None) -> Path:
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root.parent / "config" / ".env"


def _secret_file_candidate(env_file: Path, value: str) -> Path | None:
    value = value.strip().strip('"').strip("'")
    if not value or value == "your_api_key" or value.startswith(("sk-", "ak-")):
        return None

    path = Path(value)
    if not path.is_absolute():
        path = env_file.parent / path

    looks_like_path = value.lower().endswith((".env", ".txt")) or "/" in value or "\\" in value
    if path.is_file() or looks_like_path:
        return path
    return None


def _read_secret_file(path: Path, key: str) -> str:
    if not path.is_file():
        return ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return line.strip().strip('"').strip("'")

        file_key, value = line.split("=", 1)
        file_key = file_key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if file_key == key:
            return value
    return ""


def resolve_file_backed_secrets(env_file: str | Path) -> None:
    env_path = Path(env_file)
    for key in FILE_BACKED_SECRET_KEYS:
        candidate = _secret_file_candidate(env_path, os.getenv(key, ""))
        if candidate is None:
            continue
        secret = _read_secret_file(candidate, key)
        if secret:
            os.environ[key] = secret


def load_backend_env(backend_dir: str | Path | None = None) -> bool:
    """Load config/.env only for manual backend runs.

    start.py injects config/.env into child process environments and sets
    RAGNOTEBOOK_ENV_INJECTED=1. In that mode config/.env must not be read again.
    """
    if is_env_injected():
        return False

    env_file = config_env_file(backend_dir)
    loaded = load_dotenv(env_file)
    resolve_file_backed_secrets(env_file)
    return loaded
