import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.logger_handler import logger
from mvc.models.base import Base
from utils.env_loader import load_backend_env

# 加载环境变量
load_backend_env()

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
    """Initialize PostgreSQL schema for application startup."""
    from mvc.models import chat_history, document, mind_map, note, note_template, review_record, runtime_state, storage_object, study_test, user_model  # noqa: F401

    from db.pg_auto_init import auto_init_postgres, is_pg_auto_init_enabled

    if is_pg_auto_init_enabled():
        await auto_init_postgres()
        return

    if os.getenv("DB_AUTO_CREATE_TABLES", "false").lower() != "true":
        logger.info("PG_AUTO_INIT=false 且 DB_AUTO_CREATE_TABLES=false，启动时跳过数据库结构初始化")
        return

    logger.warning("DB_AUTO_CREATE_TABLES=true，仅建议本地临时环境使用")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
