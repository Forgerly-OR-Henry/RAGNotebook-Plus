"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import uuid as _uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from mvc.models.base import Base


def generate_uuid() -> str:
    """
    用途：生成generate uuid相关的数据或流程。

    参数：无显式业务参数。

    返回：str；返回值供调用方继续编排业务流程或生成接口响应。
    """
    return _uuid.uuid4().hex[:24]


class UserStatusChoice:
    """
    用途：领域对象或协作组件，用于承载本模块内的核心状态和行为。

    属性：
    - LOCKED（类属性或 ORM 字段）：保存LOCKED相关状态、配置或数据字段。
    - ACTIVE（类属性或 ORM 字段）：保存ACTIVE相关状态、配置或数据字段。
    - DISABLED（类属性或 ORM 字段）：保存DISABLED相关状态、配置或数据字段。
    """
    LOCKED = 2
    ACTIVE = 1
    DISABLED = 0


class User(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - uuid（类属性或 ORM 字段）：保存uuid相关状态、配置或数据字段。
    - username（类属性或 ORM 字段）：保存username相关状态、配置或数据字段。
    - email（类属性或 ORM 字段）：保存email相关状态、配置或数据字段。
    - telephone（类属性或 ORM 字段）：保存telephone相关状态、配置或数据字段。
    - password（类属性或 ORM 字段）：保存password相关状态、配置或数据字段。
    - is_active（类属性或 ORM 字段）：保存is_active相关状态、配置或数据字段。
    - status（类属性或 ORM 字段）：保存status相关状态、配置或数据字段。
    - gender（类属性或 ORM 字段）：保存gender相关状态、配置或数据字段。
    - bio（类属性或 ORM 字段）：保存bio相关状态、配置或数据字段。
    - avatar（类属性或 ORM 字段）：保存avatar相关状态、配置或数据字段。
    - date_joined（类属性或 ORM 字段）：保存date_joined相关状态、配置或数据字段。
    - last_login（类属性或 ORM 字段）：保存last_login相关状态、配置或数据字段。
    """
    __tablename__ = "app_users"

    uuid = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    telephone = Column(String(11), unique=True, nullable=True)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    status = Column(Integer, default=UserStatusChoice.DISABLED)
    gender = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    avatar = Column(String(255), nullable=True)
    date_joined = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
