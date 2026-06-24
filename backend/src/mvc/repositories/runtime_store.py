"""
模块职责：仓储模块，负责封装持久化或运行时状态读写逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any

from sqlalchemy import delete, select

from db.db_config import AsyncSessionLocal
from mvc.models.runtime_state import AppCache, RateLimitCounter, TokenBlacklist


def _now() -> datetime:
    """
    用途：执行now相关业务逻辑。

    参数：无显式业务参数。

    返回：datetime；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return datetime.now(timezone.utc)


async def check_runtime_store_connection() -> bool:
    """
    用途：检查check runtime store connection相关的数据或流程。

    参数：无显式业务参数。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(AppCache.key).limit(1))
        return True
    except Exception as exc:
        print(f"PostgreSQL运行态存储连接失败: {exc}")
        return False


async def get_cache(key: str) -> Any | None:
    """
    用途：读取或查询get cache相关的数据或流程。

    参数：
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：Any | None；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as session:
        item = await session.get(AppCache, key)
        if not item:
            return None
        if item.expires_at <= _now():
            await session.delete(item)
            await session.commit()
            return None
        return item.value


async def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """
    用途：异步执行set cache相关业务流程。

    参数：
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。
    - value（Any）：调用方传入的value数据或控制参数，用于驱动本函数处理流程。
    - expire（int）：调用方传入的expire数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    expires_at = _now() + timedelta(seconds=expire)
    async with AsyncSessionLocal() as session:
        item = await session.get(AppCache, key)
        if item:
            item.value = value
            item.expires_at = expires_at
        else:
            session.add(AppCache(key=key, value=value, expires_at=expires_at))
        await session.commit()
    return True


async def delete_cache(key: str) -> bool:
    """
    用途：删除delete cache相关的数据或流程。

    参数：
    - key（str）：调用方传入的key数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as session:
        item = await session.get(AppCache, key)
        if item:
            await session.delete(item)
            await session.commit()
    return True


async def delete_cache_pattern(pattern: str) -> int:
    """
    用途：删除delete cache pattern相关的数据或流程。

    参数：
    - pattern（str）：调用方传入的pattern数据或控制参数，用于驱动本函数处理流程。

    返回：int；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AppCache.key))
        keys = [key for key in result.scalars().all() if fnmatch(key, pattern)]
        if keys:
            await session.execute(delete(AppCache).where(AppCache.key.in_(keys)))
            await session.commit()
        return len(keys)


async def blacklist_jti(jti: str, expires_at: datetime) -> None:
    """
    用途：异步执行blacklist jti相关业务流程。

    参数：
    - jti（str）：调用方传入的jti数据或控制参数，用于驱动本函数处理流程。
    - expires_at（datetime）：调用方传入的expires_at数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as session:
        existing = await session.get(TokenBlacklist, jti)
        if existing:
            existing.expires_at = expires_at
        else:
            session.add(TokenBlacklist(jti=jti, expires_at=expires_at))
        await session.commit()


async def is_jti_blacklisted(jti: str) -> bool:
    """
    用途：异步执行is jti blacklisted相关业务流程。

    参数：
    - jti（str）：调用方传入的jti数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    async with AsyncSessionLocal() as session:
        item = await session.get(TokenBlacklist, jti)
        if not item:
            return False
        if item.expires_at <= _now():
            await session.delete(item)
            await session.commit()
            return False
        return True


async def hit_rate_limit(key: str, limit: int, window: int) -> bool:
    """Return True when the request should be blocked."""
    now = _now()
    expires_at = now + timedelta(seconds=window)
    async with AsyncSessionLocal() as session:
        counter = await session.get(RateLimitCounter, key)
        if not counter or counter.expires_at <= now:
            if counter:
                counter.count = 1
                counter.expires_at = expires_at
            else:
                session.add(RateLimitCounter(key=key, count=1, expires_at=expires_at))
            await session.commit()
            return False

        if counter.count >= limit:
            return True

        counter.count += 1
        await session.commit()
        return False


async def cleanup_expired_runtime_state() -> None:
    """
    用途：异步执行cleanup expired runtime state相关业务流程。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    now = _now()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AppCache).where(AppCache.expires_at <= now))
        await session.execute(delete(TokenBlacklist).where(TokenBlacklist.expires_at <= now))
        await session.execute(delete(RateLimitCounter).where(RateLimitCounter.expires_at <= now))
        await session.commit()
