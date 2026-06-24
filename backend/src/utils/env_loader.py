"""
模块职责：通用工具模块，提供跨业务复用的配置、文件、路径或安全辅助函数。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


INJECTED_ENV_FLAG = "RAGNOTEBOOK_ENV_INJECTED"
FILE_BACKED_SECRET_KEYS = ("ALIYUN_ACCESS_KEY_SECRET",)


def is_env_injected() -> bool:
    """
    用途：执行is env injected相关业务逻辑。

    参数：无显式业务参数。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return os.getenv(INJECTED_ENV_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def backend_root() -> Path:
    """
    用途：执行backend root相关业务逻辑。

    参数：无显式业务参数。

    返回：Path；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return Path(__file__).resolve().parents[2]


def config_env_file(backend_dir: str | Path | None = None) -> Path:
    """
    用途：执行config env file相关业务逻辑。

    参数：
    - backend_dir（str | Path | None）：调用方传入的backend_dir数据或控制参数，用于驱动本函数处理流程。

    返回：Path；返回值供调用方继续编排业务流程或生成接口响应。
    """
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root.parent / "config" / ".env"


def backend_env_file(backend_dir: str | Path | None = None) -> Path:
    """
    用途：执行backend env file相关业务逻辑。

    参数：
    - backend_dir（str | Path | None）：调用方传入的backend_dir数据或控制参数，用于驱动本函数处理流程。

    返回：Path；返回值供调用方继续编排业务流程或生成接口响应。
    """
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root / ".env"


def backend_env_example_file(backend_dir: str | Path | None = None) -> Path:
    """
    用途：执行backend env example file相关业务逻辑。

    参数：
    - backend_dir（str | Path | None）：调用方传入的backend_dir数据或控制参数，用于驱动本函数处理流程。

    返回：Path；返回值供调用方继续编排业务流程或生成接口响应。
    """
    root = Path(backend_dir) if backend_dir is not None else backend_root()
    return root / ".env.example"


def _env_file_keys(path: Path) -> set[str]:
    """
    用途：执行env file keys相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。

    返回：set[str]；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：校验validate env declares template keys相关的数据或流程。

    参数：
    - env_file（str | Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。
    - example_file（str | Path）：调用方传入的example_file数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行require env declared相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if name not in os.environ:
        raise RuntimeError(f"缺少环境变量 {name}。请在当前 .env 中显式声明该字段。")
    return os.environ[name].strip()


def optional_env_value(name: str, default_if_missing: str = "") -> str:
    """
    用途：读取可选环境变量，缺失时返回调用方给定的默认字符串。

    参数：
    - name（str）：环境变量名，用于定位可选运行时配置。
    - default_if_missing（str）：变量缺失时使用的默认值，默认保持为空字符串。

    返回：str；已去除首尾空白的环境变量值，供兼容性配置或可选工具路径使用。
    """
    return os.getenv(name, default_if_missing).strip()


def require_env_value(name: str, default_if_blank: str | None = None) -> str:
    """
    用途：执行require env value相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
    - default_if_blank（str | None）：调用方传入的default_if_blank数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    return value


def require_env_int(name: str) -> int:
    """
    用途：执行require env int相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_declared(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值：{value}") from exc


def require_env_int_value(name: str, default_if_blank: int | None = None) -> int:
    """
    用途：执行require env int value相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
    - default_if_blank（int | None）：调用方传入的default_if_blank数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值：{value}") from exc


def require_env_bool(name: str) -> bool:
    """
    用途：执行require env bool相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_declared(name)
    return value.lower() in {"1", "true", "yes", "on"}


def require_env_bool_value(name: str, default_if_blank: bool | None = None) -> bool:
    """
    用途：执行require env bool value相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
    - default_if_blank（bool | None）：调用方传入的default_if_blank数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_declared(name)
    if value == "" and default_if_blank is not None:
        return default_if_blank
    return value.lower() in {"1", "true", "yes", "on"}


def _secret_file_candidate(env_file: Path, value: str) -> Path | None:
    """
    用途：执行secret file candidate相关业务逻辑。

    参数：
    - env_file（Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。
    - value（str）：调用方传入的value数据或控制参数，用于驱动本函数处理流程。

    返回：Path | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行read secret file相关业务逻辑。

    参数：
    - path（Path）：调用方传入的path数据或控制参数，用于驱动本函数处理流程。
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：解析并归一化resolve file backed secrets相关的数据或流程。

    参数：
    - env_file（str | Path）：调用方传入的env_file数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
