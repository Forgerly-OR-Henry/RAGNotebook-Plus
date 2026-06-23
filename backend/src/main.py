import argparse
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from utils.env_loader import load_backend_env

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_backend_env(BACKEND_DIR)

from core.background_init import init_manager
from core.failed_response_register import register_exception_handlers
from core.logger_handler import logger
from mvc.controllers import routers
from db.db_config import init_db, seed_test_user
from mvc.repositories.runtime_store import cleanup_expired_runtime_state
from mvc.services.database_session_manager import init_database_session_manager

app = FastAPI()

# 集成限流中间件（暂时注释掉，以免在调试阶段干扰正常请求）
# RateLimitMiddleware 基于令牌桶实现，每 60 秒允许 100 个请求
# 正式部署时可根据接口负载调整限流策略
# 所有限流（包括路由上的 Depends(rate_limit(...))）通过 RATE_LIMIT_ENABLED=false 一键关闭
# app.add_middleware(RateLimitMiddleware, limit=100, window=60)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
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
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
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
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化会话管理器"""
    # 初始化数据库表结构（仅支持新库/空库，不兼容旧迁移链）
    await init_db()
    logger.info("数据库表结构初始化完成")

    # 确保测试用户存在
    await seed_test_user()

    # 使用数据库版本的会话管理器
    await init_database_session_manager()
    logger.info("数据库会话管理器初始化完成")

    await cleanup_expired_runtime_state()
    logger.info("PostgreSQL运行态存储清理完成")

    # 检查并重排序模型（在后台异步加载）
    await init_manager.start()
    logger.info("部分资源正在初始化（模型加载、pgvector服务等将在后台继续加载）")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    # 关闭 SQLAlchemy 引擎（释放 asyncpg 连接池，避免 GC 时事件循环已关闭）
    from db.db_config import async_engine
    await async_engine.dispose()
    logger.info("数据库引擎已关闭")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got: {value}") from exc


def run_standalone() -> None:
    """Start backend directly with backend/.env.

    Unified startup still goes through root start.py, which injects config/.env
    and sets RAGNOTEBOOK_ENV_INJECTED=1 before importing this module.
    """
    import uvicorn

    parser = argparse.ArgumentParser(description="Start the RAGNotebook backend using backend/.env.")
    parser.add_argument("--host", help="Override BACKEND_HOST from backend/.env.")
    parser.add_argument("--port", type=int, help="Override BACKEND_PORT from backend/.env.")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn reload.")
    args = parser.parse_args()

    host = args.host or os.getenv("BACKEND_HOST", "0.0.0.0")
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
