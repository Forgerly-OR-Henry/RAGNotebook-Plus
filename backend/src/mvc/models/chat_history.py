"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base

class ChatSession(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - project_id（类属性或 ORM 字段）：保存project_id相关状态、配置或数据字段。
    - title（类属性或 ORM 字段）：保存title相关状态、配置或数据字段。
    - metadata_（类属性或 ORM 字段）：保存metadata_相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - project（类属性或 ORM 字段）：保存project相关状态、配置或数据字段。
    - messages（类属性或 ORM 字段）：保存messages相关状态、配置或数据字段。
    """
    __tablename__ = "chat_sessions"

    id = Column(String(64), primary_key=True, index=True)
    # 通过 user_id 关联用户微服务，不做物理外键约束
    user_id = Column(String(64), index=True, nullable=False)
    project_id = Column(String(36), ForeignKey("chat_projects.id", ondelete="CASCADE"), index=True, nullable=True)

    title = Column(String(255), default="新的对话")
    metadata_ = Column(JSONB, name="metadata")  # metadata 是 SQL 保留字，加下划线
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    project = relationship("ChatProject", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - session_id（类属性或 ORM 字段）：保存session_id相关状态、配置或数据字段。
    - role（类属性或 ORM 字段）：保存role相关状态、配置或数据字段。
    - content（类属性或 ORM 字段）：保存content相关状态、配置或数据字段。
    - metadata_（类属性或 ORM 字段）：保存metadata_相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - session（类属性或 ORM 字段）：保存session相关状态、配置或数据字段。
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.id"))

    # LangChain 标准字段
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column(JSONB, name="metadata")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    session = relationship("ChatSession", back_populates="messages")
