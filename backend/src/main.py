"""
模块职责：FastAPI 应用入口，负责组装路由、中间件、后台初始化与生命周期钩子。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import argparse
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from utils.env_loader import load_backend_env, require_env_bool, require_env_declared, require_env_int_value, require_env_value

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_backend_env(BACKEND_DIR)

from core.background_init import init_manager
from core.failed_response_register import register_exception_handlers
from core.logger_handler import logger
from mvc.controllers import routers
from db.db_config import init_db, seed_test_user
from mvc.repositories.runtime_store import cleanup_expired_runtime_state
from mvc.services.database_session_manager import init_database_session_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    用途：异步执行lifespan相关业务流程。

    参数：
    - _app（FastAPI）：调用方传入的_app数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app = FastAPI(lifespan=lifespan)

# 集成限流中间件（暂时注释掉，以免在调试阶段干扰正常请求）
# RateLimitMiddleware 基于令牌桶实现，每 60 秒允许 100 个请求
# 正式部署时可根据接口负载调整限流策略
# 所有限流（包括路由上的 Depends(rate_limit(...))）通过 RATE_LIMIT_ENABLED=false 一键关闭
# app.add_middleware(RateLimitMiddleware, limit=100, window=60)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    用途：异步执行add process time header相关业务流程。

    参数：
    - request（Request）：调用方传入的request数据或控制参数，用于驱动本函数处理流程。
    - call_next（未显式标注）：调用方传入的call_next数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response

# 集成API路由
for router in routers:
    app.include_router(router)




cors_origins = [
    origin.strip()
    for origin in require_env_declared("CORS_ALLOW_ORIGINS").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True, # 允许携带cookie
    allow_methods=["*"], # 允许的请求方法
    allow_headers=["*"], # 允许的请求头
)

# 注册异常处理函数
register_exception_handlers(app)

@app.get("/")
async def root():
    """
    用途：异步执行root相关业务流程。

    参数：无显式业务参数。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    return {"message": "Hello World"}


def should_seed_test_user() -> bool:
    """
    用途：执行should seed test user相关业务逻辑。

    参数：无显式业务参数。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return require_env_bool("SEED_TEST_USER")


async def startup_event():
    """应用启动时初始化会话管理器"""
    # 初始化数据库表结构（仅支持新库/空库，不兼容旧迁移链）
    await init_db()
    logger.info("数据库表结构初始化完成")

    if should_seed_test_user():
        await seed_test_user()
    else:
        logger.info("已跳过默认测试用户初始化（SEED_TEST_USER=false）")

    # 使用数据库版本的会话管理器
    await init_database_session_manager()
    logger.info("数据库会话管理器初始化完成")

    await cleanup_expired_runtime_state()
    logger.info("PostgreSQL运行态存储清理完成")

    # 检查并重排序模型（在后台异步加载）
    await init_manager.start()
    logger.info("部分资源正在初始化（模型加载、pgvector服务等将在后台继续加载）")

async def shutdown_event():
    """应用关闭时清理资源"""
    # 关闭 SQLAlchemy 引擎（释放 asyncpg 连接池，避免 GC 时事件循环已关闭）
    from db.db_config import async_engine
    await async_engine.dispose()
    logger.info("数据库引擎已关闭")


def _env_int(name: str, default: int) -> int:
    """
    用途：执行env int相关业务逻辑。

    参数：
    - name（str）：调用方传入的name数据或控制参数，用于驱动本函数处理流程。
    - default（int）：调用方传入的default数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。
    """
    try:
        return require_env_int_value(name, default)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def run_standalone() -> None:
    """Start backend directly with backend/config/.env.

    Unified startup still goes through root start.py, which injects config/.env
    and sets RAGNOTEBOOK_ENV_INJECTED=1 before importing this module.
    """
    import uvicorn

    parser = argparse.ArgumentParser(description="Start the RAGNotebook backend using backend/config/.env.")
    parser.add_argument("--host", help="Override BACKEND_HOST from backend/config/.env.")
    parser.add_argument("--port", type=int, help="Override BACKEND_PORT from backend/config/.env.")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn reload.")
    args = parser.parse_args()

    host = args.host or require_env_value("BACKEND_HOST", "0.0.0.0")
    port = args.port or _env_int("BACKEND_PORT", 10000)
    log_config = BACKEND_DIR / "config" / "uvicorn_log_config.json"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=not args.no_reload,
        reload_dirs=[str(BACKEND_DIR / "src")],
        log_config=str(log_config) if log_config.is_file() else None,
    )


if __name__ == "__main__":
    run_standalone()
