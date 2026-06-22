from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from core.logger_handler import logger
from utils.env_loader import load_backend_env


BACKEND_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = BACKEND_DIR / "src"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "alembic"
PUBLIC_SCHEMA = "public"
ALEMBIC_VERSION_TABLE = "alembic_version"


def _env_enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    user = os.getenv("POSTGRES_USER", "rag")
    password = os.getenv("POSTGRES_PASSWORD", "rag")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "rag_notebook")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


async def _schema_has_application_tables() -> bool:
    engine = create_async_engine(
        _database_url(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": PUBLIC_SCHEMA}},
    )
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                      AND table_type = 'BASE TABLE'
                      AND table_name <> :alembic_version_table
                    LIMIT 1
                    """
                ),
                {
                    "schema": PUBLIC_SCHEMA,
                    "alembic_version_table": ALEMBIC_VERSION_TABLE,
                },
            )
            return result.scalar_one_or_none() is not None
    finally:
        await engine.dispose()


async def _schema_has_alembic_version() -> bool:
    engine = create_async_engine(
        _database_url(),
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": PUBLIC_SCHEMA}},
    )
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                      AND table_name = :alembic_version_table
                    LIMIT 1
                    """
                ),
                {
                    "schema": PUBLIC_SCHEMA,
                    "alembic_version_table": ALEMBIC_VERSION_TABLE,
                },
            )
            return result.scalar_one_or_none() is not None
    finally:
        await engine.dispose()


def is_pg_auto_init_enabled() -> bool:
    return _env_enabled("PG_AUTO_INIT", "true")


def _load_alembic_api():
    original_sys_path = sys.path[:]
    backend_dir = BACKEND_DIR.resolve()

    for entry in list(sys.path):
        resolved = Path(entry or os.getcwd()).resolve()
        if resolved == backend_dir:
            sys.path.remove(entry)

    for module_name in list(sys.modules):
        if module_name == "alembic" or module_name.startswith("alembic."):
            module = sys.modules[module_name]
            module_file = getattr(module, "__file__", None)
            if module_file is None or str(Path(module_file).resolve()).startswith(str(ALEMBIC_DIR.resolve())):
                sys.modules.pop(module_name, None)

    try:
        from alembic import command
        from alembic.config import Config
    finally:
        sys.path[:] = original_sys_path

    return command, Config


def _build_alembic_config():
    if not ALEMBIC_INI.exists():
        raise FileNotFoundError(f"Alembic config not found: {ALEMBIC_INI}")
    if not ALEMBIC_DIR.exists():
        raise FileNotFoundError(f"Alembic script directory not found: {ALEMBIC_DIR}")

    _, Config = _load_alembic_api()
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("prepend_sys_path", str(SRC_DIR))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option("sqlalchemy.url", _database_url())
    return config


def _upgrade_head() -> None:
    load_backend_env(BACKEND_DIR)
    command, _ = _load_alembic_api()
    command.upgrade(_build_alembic_config(), "head")


def _describe_init_error(exc: Exception) -> str:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current:
        chain.append(current)
        current = current.__cause__ or current.__context__

    if any(error.__class__.__name__ == "InvalidPasswordError" for error in chain):
        return "数据库认证失败，请检查 config/.env 中 DATABASE_URL 与 POSTGRES_USER/POSTGRES_PASSWORD 是否一致"
    if any(error.__class__.__name__ == "InvalidCatalogNameError" for error in chain):
        return "目标数据库不存在，请先创建 POSTGRES_DB 指定的数据库"
    if any(error.__class__.__name__ in {"InvalidAuthorizationSpecificationError", "InvalidRoleSpecificationError"} for error in chain):
        return "数据库用户不存在或无权限，请先创建 POSTGRES_USER 指定的用户并授权 public schema"
    if any(error.__class__.__name__ in {"ConnectionRefusedError", "OSError"} for error in chain):
        return "无法连接 PostgreSQL，请确认服务已启动且 host/port 配置正确"
    return str(exc)


async def auto_init_postgres(force: bool = False) -> bool:
    """Initialize an existing PostgreSQL database only when it has no app tables.

    This expects the PostgreSQL user and database to already exist. It only
    manages tables and the Alembic version table in the public schema.
    """
    load_backend_env(BACKEND_DIR)

    if not force and not is_pg_auto_init_enabled():
        logger.info("PG_AUTO_INIT=false，跳过 PostgreSQL 自动初始化")
        return False

    if not force and await _schema_has_application_tables():
        if await _schema_has_alembic_version():
            logger.info("public schema 已存在业务表，执行 Alembic upgrade head 以应用新增迁移")
            await asyncio.to_thread(_upgrade_head)
            return True
        logger.info("public schema 已存在业务表但没有 alembic_version，跳过 PostgreSQL 自动初始化")
        return False

    logger.info("开始执行 PostgreSQL 自动初始化，schema=public")
    try:
        await asyncio.to_thread(_upgrade_head)
    except Exception as exc:
        logger.error("PostgreSQL 自动初始化失败：%s", _describe_init_error(exc))
        raise

    logger.info("PostgreSQL 自动初始化完成")
    return True


async def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL schema for RAGNotebook.")
    parser.add_argument("--force", action="store_true", help="Run Alembic upgrade even when application tables already exist.")
    args = parser.parse_args(argv)
    await auto_init_postgres(force=args.force)


if __name__ == "__main__":
    try:
        asyncio.run(_main(sys.argv[1:]))
    except Exception as exc:
        print(f"PostgreSQL 自动初始化失败：{_describe_init_error(exc)}", file=sys.stderr)
        raise SystemExit(1)
