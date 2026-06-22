from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Any

from sqlalchemy import delete, select

from db.db_config import AsyncSessionLocal
from mvc.models.runtime_state import AppCache, RateLimitCounter, TokenBlacklist


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def check_runtime_store_connection() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(AppCache.key).limit(1))
        return True
    except Exception as exc:
        print(f"PostgreSQL运行态存储连接失败: {exc}")
        return False


async def get_cache(key: str) -> Any | None:
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
    async with AsyncSessionLocal() as session:
        item = await session.get(AppCache, key)
        if item:
            await session.delete(item)
            await session.commit()
    return True


async def delete_cache_pattern(pattern: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AppCache.key))
        keys = [key for key in result.scalars().all() if fnmatch(key, pattern)]
        if keys:
            await session.execute(delete(AppCache).where(AppCache.key.in_(keys)))
            await session.commit()
        return len(keys)


async def blacklist_jti(jti: str, expires_at: datetime) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.get(TokenBlacklist, jti)
        if existing:
            existing.expires_at = expires_at
        else:
            session.add(TokenBlacklist(jti=jti, expires_at=expires_at))
        await session.commit()


async def is_jti_blacklisted(jti: str) -> bool:
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
    now = _now()
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AppCache).where(AppCache.expires_at <= now))
        await session.execute(delete(TokenBlacklist).where(TokenBlacklist.expires_at <= now))
        await session.execute(delete(RateLimitCounter).where(RateLimitCounter.expires_at <= now))
        await session.commit()
