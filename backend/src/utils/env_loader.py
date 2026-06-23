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


def backend_env_file(backend_dir: str | Path | None = None) -> Path:
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root / ".env"


def backend_env_example_file(backend_dir: str | Path | None = None) -> Path:
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root / ".env.example"


def _env_file_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip().lstrip("\ufeff")
        if key:
            keys.add(key)
    return keys


def validate_env_declares_template_keys(env_file: str | Path, example_file: str | Path) -> None:
    env_path = Path(env_file)
    example_path = Path(example_file)
    if not env_path.exists() or not example_path.exists():
        return

    missing = sorted(_env_file_keys(example_path) - _env_file_keys(env_path))
    if missing:
        raise RuntimeError(
            f"{env_path} 缺少配置字段: {', '.join(missing)}。"
            f"请参考 {example_path} 补齐字段；字段值可以为空或使用模板默认值，但字段必须显式存在。"
        )


def require_env_declared(name: str) -> str:
    if name not in os.environ:
        raise RuntimeError(f"缺少环境变量 {name}。请在当前 .env 中显式声明该字段。")
    return os.environ[name].strip()


def require_env_value(name: str, default_if_blank: str | None = None) -> str:
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    return value


def require_env_int(name: str) -> int:
    value = require_env_declared(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值：{value}") from exc


def require_env_int_value(name: str, default_if_blank: int | None = None) -> int:
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值：{value}") from exc


def require_env_bool(name: str) -> bool:
    value = require_env_declared(name)
    return value.lower() in {"1", "true", "yes", "on"}


def require_env_bool_value(name: str, default_if_blank: bool | None = None) -> bool:
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    return value.lower() in {"1", "true", "yes", "on"}


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
    """Load runtime env for manual backend runs.

    start.py injects config/.env into child process environments and sets
    RAGNOTEBOOK_ENV_INJECTED=1. In that mode config/.env must not be read again.
    Manual backend runs read backend/.env only.
    """
    if is_env_injected():
        return False

    env_file = backend_env_file(backend_dir)
    loaded = load_dotenv(env_file)
    validate_env_declares_template_keys(env_file, backend_env_example_file(backend_dir))
    resolve_file_backed_secrets(env_file)
    return loaded
