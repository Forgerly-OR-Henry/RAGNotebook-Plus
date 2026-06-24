"""
模块职责：测试模块，使用单元测试和回归用例验证当前业务契约。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import os
from pathlib import Path

import pytest

from utils.env_loader import backend_env_file, config_env_file, load_backend_env, validate_env_declares_template_keys


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_KEYS = {
    "BACKEND_HOST",
    "BACKEND_PORT",
    "CORS_ALLOW_ORIGINS",
    "DATABASE_URL",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "SQL_ECHO",
    "FILE_STORAGE_HOST",
    "FILE_STORAGE_PROTOCOL",
    "FILE_STORAGE_PORT",
    "FILE_STORAGE_USERNAME",
    "FILE_STORAGE_PASSWORD",
    "FILE_STORAGE_BASE_DIR",
    "FILE_STORAGE_URI_ALIAS",
    "ALIYUN_ACCESS_KEY_SECRET",
    "DASHSCOPE_API_KEY",
    "ALIYUN_BASE_URL",
    "OLLAMA_BASE_URL",
    "LLM_TYPE",
    "CHAT_API_KEY",
    "CHAT_MODEL_NAME",
    "ALIYUN_MODEL_NAME",
    "OLLAMA_MODEL_NAME",
    "OLLAMA_CHAT_MODEL_NAME",
    "EMBED_MODEL_TYPE",
    "ALIYUN_EMBED_MODEL_NAME",
    "TEXT_EMBEDDING_MODEL_NAME",
    "EMBEDDING_DIM",
    "VISION_MODEL_TYPE",
    "VISION_CHAT_MODEL_NAME",
    "VISION_OLLAMA_MODEL_NAME",
    "VISION_BATCH_SIZE",
    "VISION_DEDUP_ENABLED",
    "VISION_DEDUP_THRESHOLD",
    "VISION_BATCH_LOW_RES",
    "RERANKER_MODEL_PATH",
    "RATE_LIMIT_ENABLED",
    "SEED_TEST_USER",
    "CHAT_HISTORY_TURNS",
    "QUERY_EMBEDDING_CACHE_MAX",
    "TOKEN_BLACKLIST_CACHE_TTL_SECONDS",
    "SECRET_KEY",
    "ALGORITHM",
}


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
        keys.add(line.split("=", 1)[0].strip().lstrip("\ufeff"))
    return keys


def test_backend_env_path_is_separate_from_global_config(tmp_path: Path):
    """
    用途：执行test backend env path is separate from global config相关业务逻辑。

    参数：
    - tmp_path（Path）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    backend_dir = tmp_path / "backend"
    config_dir = tmp_path / "config"
    backend_dir.mkdir()
    config_dir.mkdir()
    (backend_dir / ".env").write_text("BACKEND_PORT=10001\n", encoding="utf-8")
    (config_dir / ".env").write_text("BACKEND_PORT=10000\n", encoding="utf-8")

    assert config_env_file(backend_dir) == config_dir / ".env"
    assert backend_env_file(backend_dir) == backend_dir / ".env"


def test_manual_backend_load_reads_backend_env_only(tmp_path: Path, monkeypatch):
    """
    用途：执行test manual backend load reads backend env only相关业务逻辑。

    参数：
    - tmp_path（Path）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
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
    """
    用途：执行test injected env skips backend env相关业务逻辑。

    参数：
    - tmp_path（Path）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。
    - monkeypatch（未显式标注）：调用方传入的monkeypatch数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / ".env").write_text("BACKEND_PORT=10001\n", encoding="utf-8")

    monkeypatch.delenv("BACKEND_PORT", raising=False)
    monkeypatch.setenv("RAGNOTEBOOK_ENV_INJECTED", "1")

    assert load_backend_env(backend_dir) is False
    assert "BACKEND_PORT" not in os.environ


def test_env_file_validation_rejects_missing_template_fields(tmp_path: Path):
    """
    用途：执行test env file validation rejects missing template fields相关业务逻辑。

    参数：
    - tmp_path（Path）：调用方传入的tmp_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    env_file = tmp_path / ".env"
    example_file = tmp_path / ".env.example"
    env_file.write_text("A=1\n", encoding="utf-8")
    example_file.write_text("A=1\nB=\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="B"):
        validate_env_declares_template_keys(env_file, example_file)


@pytest.mark.parametrize(
    "relative_path",
    ["config/.env.example", "backend/.env.example"],
)
def test_runtime_config_keys_are_declared_in_env_templates(relative_path: str):
    """
    用途：执行test runtime config keys are declared in env templates相关业务逻辑。

    参数：
    - relative_path（str）：调用方传入的relative_path数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    assert RUNTIME_CONFIG_KEYS <= _env_keys(REPO_ROOT / relative_path)


def test_backend_runtime_config_reads_go_through_env_loader():
    """
    用途：执行test backend runtime config reads go through env loader相关业务逻辑。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
    """
    offenders = []
    for path in (REPO_ROOT / "backend" / "src").rglob("*.py"):
        if path.as_posix().endswith("backend/src/utils/env_loader.py"):
            continue
        if "os.getenv(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []
