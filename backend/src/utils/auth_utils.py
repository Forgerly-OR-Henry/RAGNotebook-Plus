import os
import time
import uuid
from typing import Any
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from core.failed_response import logger
from db.db_config import AsyncSessionLocal
from mvc.repositories.runtime_store import blacklist_jti, delete_cache, get_cache, is_jti_blacklisted, set_cache
from utils.env_loader import load_backend_env

load_backend_env()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

security = HTTPBearer()

pwd_context = CryptContext(schemes=["bcrypt", "django_pbkdf2_sha256"], deprecated="auto")

_BLACKLIST_CACHE_TTL_SECONDS = float(os.getenv("TOKEN_BLACKLIST_CACHE_TTL_SECONDS", "5"))
_BLACKLIST_CACHE_MAX_SIZE = 10000
_blacklist_cache: dict[str, tuple[bool, float]] = {}


def _get_cached_blacklist_status(jti: str) -> bool | None:
    cached = _blacklist_cache.get(jti)
    if not cached:
        return None

    revoked, expires_at = cached
    if expires_at <= time.time():
        _blacklist_cache.pop(jti, None)
        return None
    return revoked


def _cache_blacklist_status(jti: str, revoked: bool, ttl_seconds: float | None = None) -> None:
    if len(_blacklist_cache) >= _BLACKLIST_CACHE_MAX_SIZE:
        _blacklist_cache.clear()

    ttl = _BLACKLIST_CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    _blacklist_cache[jti] = (revoked, time.time() + max(ttl, 0))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def generate_token(user_id: str, username: str, email: str) -> tuple[str, int]:
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
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def blacklist_token(token: str):
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
