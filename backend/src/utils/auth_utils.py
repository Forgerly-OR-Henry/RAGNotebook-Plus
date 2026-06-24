"""
模块职责：认证工具模块，负责 JWT、密码哈希和用户令牌校验等安全基础能力。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from core.failed_response import logger
from db.db_config import AsyncSessionLocal
from mvc.repositories.runtime_store import blacklist_jti, delete_cache, get_cache, is_jti_blacklisted, set_cache
from utils.env_loader import load_backend_env, require_env_value

load_backend_env()

SECRET_KEY = require_env_value("SECRET_KEY")
ALGORITHM = require_env_value("ALGORITHM")

security = HTTPBearer()


def _ensure_bcrypt_about_metadata() -> None:
    """
    用途：校验并确保ensure bcrypt about metadata相关的数据或流程。

    参数：无显式业务参数。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if hasattr(_bcrypt, "__about__"):
        return

    try:
        bcrypt_version = package_version("bcrypt")
    except PackageNotFoundError:
        bcrypt_version = "unknown"

    _bcrypt.__about__ = type("_BcryptAbout", (), {"__version__": bcrypt_version})()


_ensure_bcrypt_about_metadata()

pwd_context = CryptContext(schemes=["bcrypt", "django_pbkdf2_sha256"], deprecated="auto")


def _blacklist_cache_ttl_seconds() -> float:
    """
    用途：执行blacklist cache ttl seconds相关业务逻辑。

    参数：无显式业务参数。

    返回：float；返回值供调用方继续编排业务流程或生成接口响应。
    """
    value = require_env_value("TOKEN_BLACKLIST_CACHE_TTL_SECONDS", "5")
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"TOKEN_BLACKLIST_CACHE_TTL_SECONDS 必须是数字，当前值：{value}") from exc


_BLACKLIST_CACHE_TTL_SECONDS = _blacklist_cache_ttl_seconds()
_BLACKLIST_CACHE_MAX_SIZE = 10000
_blacklist_cache: dict[str, tuple[bool, float]] = {}


def _get_cached_blacklist_status(jti: str) -> bool | None:
    """
    用途：读取或查询get cached blacklist status相关的数据或流程。

    参数：
    - jti（str）：调用方传入的jti数据或控制参数，用于驱动本函数处理流程。

    返回：bool | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    cached = _blacklist_cache.get(jti)
    if not cached:
        return None

    revoked, expires_at = cached
    if expires_at <= time.time():
        _blacklist_cache.pop(jti, None)
        return None
    return revoked


def _cache_blacklist_status(jti: str, revoked: bool, ttl_seconds: float | None = None) -> None:
    """
    用途：执行cache blacklist status相关业务逻辑。

    参数：
    - jti（str）：调用方传入的jti数据或控制参数，用于驱动本函数处理流程。
    - revoked（bool）：调用方传入的revoked数据或控制参数，用于驱动本函数处理流程。
    - ttl_seconds（float | None）：调用方传入的ttl_seconds数据或控制参数，用于驱动本函数处理流程。

    返回：None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    if len(_blacklist_cache) >= _BLACKLIST_CACHE_MAX_SIZE:
        _blacklist_cache.clear()

    ttl = _BLACKLIST_CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    _blacklist_cache[jti] = (revoked, time.time() + max(ttl, 0))


def hash_password(password: str) -> str:
    """
    用途：执行hash password相关业务逻辑。

    参数：
    - password（str）：调用方传入的password数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    用途：执行verify password相关业务逻辑。

    参数：
    - plain_password（str）：调用方传入的plain_password数据或控制参数，用于驱动本函数处理流程。
    - hashed_password（str）：调用方传入的hashed_password数据或控制参数，用于驱动本函数处理流程。

    返回：bool；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token(user_id: str, username: str, email: str) -> tuple[str, int]:
    """
    用途：生成generate token相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - username（str）：调用方传入的username数据或控制参数，用于驱动本函数处理流程。
    - email（str）：调用方传入的email数据或控制参数，用于驱动本函数处理流程。

    返回：tuple[str, int]；返回值供调用方继续编排业务流程或生成接口响应。
    """
    expire_time = int(time.time()) + 60 * 60 * 24
    payload = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "exp": expire_time,
        "iat": int(time.time()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire_time


def decode_django_jwt(token: str) -> dict[str, Any] | None:
    """
    用途：执行decode django jwt相关业务逻辑。

    参数：
    - token（str）：调用方传入的token数据或控制参数，用于驱动本函数处理流程。

    返回：dict[str, Any] | None；返回值供调用方继续编排业务流程或生成接口响应。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def blacklist_token(token: str):
    """
    用途：异步执行blacklist token相关业务流程。

    参数：
    - token（str）：调用方传入的token数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    payload = decode_django_jwt(token)
    if not payload:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        try:
            await blacklist_jti(jti, datetime.fromtimestamp(exp, timezone.utc))
            _cache_blacklist_status(jti, True, exp - time.time())
        except Exception as e:
            logger.warning(f"黑名单Token失败: {e}")


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    用途：读取或查询get current user id相关的数据或流程。

    参数：
    - credentials（HTTPAuthorizationCredentials）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    token = credentials.credentials
    payload = decode_django_jwt(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if jti:
        cached_blacklisted = _get_cached_blacklist_status(jti)
        if cached_blacklisted is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            blacklisted = cached_blacklisted
            if blacklisted is None:
                blacklisted = await is_jti_blacklisted(jti)
                _cache_blacklist_status(jti, blacklisted)

            if blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Token黑名单检查失败，跳过: {e}")

    user_id: str = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not find user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_user_info_from_db(user_id: str) -> dict[str, Any] | None:
    """
    用途：读取或查询get user info from db相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。

    返回：dict[str, Any] | None；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    from mvc.models.user_model import User

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.uuid == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "uuid": user.uuid,
            "user_id": user.uuid,
            "id": user.uuid,
            "username": user.username,
            "email": user.email,
            "telephone": user.telephone,
            "gender": user.gender,
            "bio": user.bio,
            "avatar": user.avatar,
            "status": user.status,
            "date_joined": str(user.date_joined) if user.date_joined else None,
            "last_login": str(user.last_login) if user.last_login else None,
            "is_active": user.is_active,
        }


async def get_user_info_cached(user_id: str, credentials: HTTPAuthorizationCredentials | None = None):
    """
    用途：读取或查询get user info cached相关的数据或流程。

    参数：
    - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
    - credentials（HTTPAuthorizationCredentials | None）：调用方传入的credentials数据或控制参数，用于驱动本函数处理流程。

    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
    """
    key = f"user:{user_id}"

    try:
        user_info = await get_cache(key)
        if user_info is not None:
            return user_info

        user_data = await get_user_info_from_db(user_id)
        if user_data:
            await set_cache(key, user_data, expire=3600)
            return user_data
        return None
    except Exception:
        await delete_cache(key)
        user_data = await get_user_info_from_db(user_id)
        if user_data:
            await set_cache(key, user_data, expire=3600)
        return user_data
        return None
