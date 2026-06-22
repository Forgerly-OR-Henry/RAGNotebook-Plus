import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
PUBLIC_SCHEMA = "public"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.chat_history import Base
from utils.env_loader import load_backend_env

# Import all models so Alembic sees complete metadata.
from models import chat_history, knowledge_document, mind_map, note, note_template, review_record, runtime_state, study_test, user_model  # noqa: F401

load_backend_env(BACKEND_DIR)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured
    user = os.getenv("POSTGRES_USER", "rag")
    password = os.getenv("POSTGRES_PASSWORD", "rag")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "rag_notebook")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=PUBLIC_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=PUBLIC_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.execute(text("SET search_path TO public"))
        await connection.execute(text("SELECT pg_advisory_lock(hashtext('ragnotebook_public_schema_init'))"))
        try:
            await connection.run_sync(do_run_migrations)
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(hashtext('ragnotebook_public_schema_init'))"))
            await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
