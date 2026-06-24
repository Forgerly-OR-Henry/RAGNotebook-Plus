"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class ChatProject(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - name（类属性或 ORM 字段）：保存name相关状态、配置或数据字段。
    - description（类属性或 ORM 字段）：保存description相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - sources（类属性或 ORM 字段）：保存sources相关状态、配置或数据字段。
    - sessions（类属性或 ORM 字段）：保存sessions相关状态、配置或数据字段。
    """
    __tablename__ = "chat_projects"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(64), index=True, nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sources = relationship("ProjectSource", back_populates="project", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")


class ProjectSource(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - project_id（类属性或 ORM 字段）：保存project_id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - source_type（类属性或 ORM 字段）：保存source_type相关状态、配置或数据字段。
    - source_id（类属性或 ORM 字段）：保存source_id相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - project（类属性或 ORM 字段）：保存project相关状态、配置或数据字段。
    """
    __tablename__ = "project_sources"
    __table_args__ = (
        UniqueConstraint("project_id", "source_type", "source_id", name="uq_project_source_ref"),
    )

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("chat_projects.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(64), index=True, nullable=False)
    source_type = Column(String(20), nullable=False)
    source_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("ChatProject", back_populates="sources")
