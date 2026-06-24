"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from mvc.models.base import Base


class AppCache(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - key（类属性或 ORM 字段）：保存key相关状态、配置或数据字段。
    - value（类属性或 ORM 字段）：保存value相关状态、配置或数据字段。
    - expires_at（类属性或 ORM 字段）：保存expires_at相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    """
    __tablename__ = "app_cache_entries"

    key = Column(String(255), primary_key=True)
    value = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TokenBlacklist(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - jti（类属性或 ORM 字段）：保存jti相关状态、配置或数据字段。
    - expires_at（类属性或 ORM 字段）：保存expires_at相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    """
    __tablename__ = "auth_revoked_tokens"

    jti = Column(String(64), primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RateLimitCounter(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - key（类属性或 ORM 字段）：保存key相关状态、配置或数据字段。
    - count（类属性或 ORM 字段）：保存count相关状态、配置或数据字段。
    - expires_at（类属性或 ORM 字段）：保存expires_at相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    """
    __tablename__ = "rate_limit_buckets"

    key = Column(String(255), primary_key=True)
    count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
