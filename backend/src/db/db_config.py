import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.logger_handler import logger
from mvc.models.base import Base
from utils.env_loader import load_backend_env

# 加载环境变量
load_backend_env()

PUBLIC_SCHEMA = "public"
INDEX_CHUNKS_TABLE = "index_chunks"
CURRENT_EXTRA_TABLES = {INDEX_CHUNKS_TABLE}

INDEX_CHUNKS_COLUMNS = {
    "id",
    "document_id",
    "user_id",
    "source_type",
    "chunk_index",
    "content",
    "content_hash",
    "metadata",
    "embedding",
    "created_at",
    "updated_at",
}

RESET_DATABASE_HINT = (
    "当前版本只支持新库/空库，不再兼容旧数据库迁移。"
    "请清空 PostgreSQL public schema 或重建 POSTGRES_DB 后重新启动。"
)


def _build_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    user = os.getenv("POSTGRES_USER", "rag")
    password = os.getenv("POSTGRES_PASSWORD", "rag")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "rag_notebook")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


ASYNC_DATABSE_URL = _build_database_url()

# 创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABSE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={"server_settings": {"search_path": "public"}},
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize the current schema for a new or already-current database."""
    _import_all_models()

    async with async_engine.begin() as conn:
        existing_tables = await _public_base_tables(conn)
        unsupported_tables = _unsupported_schema_tables(existing_tables)
        if unsupported_tables:
            raise RuntimeError(
                f"数据库 public schema 包含当前版本不管理的表：{_format_names(unsupported_tables)}。"
                f"{RESET_DATABASE_HINT}"
            )

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_knowledge_document_columns(conn)
        await _create_index_chunks_table(conn)
        await _backfill_knowledge_documents(conn)
        await _validate_current_schema(conn)

    logger.info("当前数据库 schema 初始化完成（仅支持新库/空库）")


def _import_all_models() -> None:
    from mvc.models import (
        chat_history,
        document,
        knowledge_document,
        knowledge_folder,
        mind_map,
        note,
        note_folder,
        note_template,
        project,
        runtime_state,
        storage_object,
        study_test,
        user_model,
    )  # noqa: F401


async def _backfill_knowledge_documents(conn) -> None:
    await conn.execute(
        text(
            """
            INSERT INTO knowledge_documents (id, user_id, document_id, title, created_at, updated_at)
            SELECT id, user_id, id, title, created_at, updated_at
            FROM documents
            WHERE source_type = 'knowledge'
              AND id NOT IN (
                  SELECT document_id
                  FROM knowledge_documents
                  WHERE document_id IS NOT NULL
              )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


async def _ensure_knowledge_document_columns(conn) -> None:
    await conn.execute(text("ALTER TABLE IF EXISTS knowledge_documents ADD COLUMN IF NOT EXISTS category VARCHAR(50)"))
    await conn.execute(text("ALTER TABLE IF EXISTS knowledge_documents ADD COLUMN IF NOT EXISTS tags JSONB"))


def _current_schema_tables() -> set[str]:
    _import_all_models()
    return set(Base.metadata.tables) | CURRENT_EXTRA_TABLES


def _unsupported_schema_tables(existing_tables: set[str]) -> set[str]:
    return existing_tables - _current_schema_tables()


def _format_names(names: set[str]) -> str:
    return ", ".join(sorted(names))


async def _public_base_tables(conn) -> set[str]:
    result = await conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_type = 'BASE TABLE'
            """
        ),
        {"schema": PUBLIC_SCHEMA},
    )
    return {row[0] for row in result}


def _embedding_dim() -> int:
    value = os.getenv("EMBEDDING_DIM", "1024")
    try:
        dim = int(value)
    except ValueError as exc:
        raise RuntimeError(f"EMBEDDING_DIM 必须是正整数，当前值：{value}") from exc
    if dim <= 0:
        raise RuntimeError(f"EMBEDDING_DIM 必须是正整数，当前值：{value}")
    return dim


async def _create_index_chunks_table(conn) -> None:
    embedding_dim = _embedding_dim()
    await conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {INDEX_CHUNKS_TABLE} (
                id VARCHAR(64) PRIMARY KEY,
                document_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                user_id VARCHAR(36) NOT NULL,
                source_type VARCHAR(20) NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding vector({embedding_dim}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{INDEX_CHUNKS_TABLE}_document_chunk ON {INDEX_CHUNKS_TABLE} (document_id, chunk_index)"))
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{INDEX_CHUNKS_TABLE}_source_user ON {INDEX_CHUNKS_TABLE} (source_type, user_id)"))
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{INDEX_CHUNKS_TABLE}_metadata ON {INDEX_CHUNKS_TABLE} USING gin (metadata jsonb_path_ops)"))
    await conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{INDEX_CHUNKS_TABLE}_embedding_hnsw ON {INDEX_CHUNKS_TABLE} USING hnsw (embedding vector_cosine_ops)"))


def _expected_schema_columns() -> dict[str, set[str]]:
    _import_all_models()
    columns = {
        table_name: {column.name for column in table.columns}
        for table_name, table in Base.metadata.tables.items()
    }
    columns[INDEX_CHUNKS_TABLE] = INDEX_CHUNKS_COLUMNS
    return columns


async def _schema_columns(conn) -> dict[str, set[str]]:
    result = await conn.execute(
        text(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
            """
        ),
        {"schema": PUBLIC_SCHEMA},
    )
    columns: dict[str, set[str]] = {}
    for table_name, column_name in result:
        columns.setdefault(table_name, set()).add(column_name)
    return columns


async def _validate_current_schema(conn) -> None:
    expected_columns = _expected_schema_columns()
    actual_columns = await _schema_columns(conn)

    missing_tables = set(expected_columns) - set(actual_columns)
    if missing_tables:
        raise RuntimeError(f"数据库缺少当前版本必需表：{_format_names(missing_tables)}。{RESET_DATABASE_HINT}")

    missing_column_messages = []
    for table_name, expected in sorted(expected_columns.items()):
        missing_columns = expected - actual_columns.get(table_name, set())
        if missing_columns:
            missing_column_messages.append(f"{table_name} 缺少列 {_format_names(missing_columns)}")

    if missing_column_messages:
        raise RuntimeError(
            "数据库 schema 与当前代码不匹配："
            + "；".join(missing_column_messages)
            + f"。{RESET_DATABASE_HINT}"
        )


# 依赖项
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        finally:
            await session.close()




async def seed_test_user():
    from mvc.models.user_model import User, UserStatusChoice
    from utils.auth_utils import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            logger.info("测试用户 admin 已存在，跳过创建")
            return

        user = User(
            username="admin",
            email="admin@example.com",
            password=hash_password("admin1234"),
            status=UserStatusChoice.ACTIVE,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        logger.info("测试用户 admin / admin1234 已自动创建")


async def check_database_connection() -> bool:
    """检查 PostgreSQL 连接"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"PostgreSQL连接失败: {e}")
        return False
