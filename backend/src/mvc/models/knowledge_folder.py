"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class KnowledgeFolder(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - parent_id（类属性或 ORM 字段）：保存parent_id相关状态、配置或数据字段。
    - name（类属性或 ORM 字段）：保存name相关状态、配置或数据字段。
    - sort_order（类属性或 ORM 字段）：保存sort_order相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - parent（类属性或 ORM 字段）：保存parent相关状态、配置或数据字段。
    - children（类属性或 ORM 字段）：保存children相关状态、配置或数据字段。
    - assignments（类属性或 ORM 字段）：保存assignments相关状态、配置或数据字段。
    """
    __tablename__ = "knowledge_folders"
    __table_args__ = (
        UniqueConstraint("user_id", "parent_id", "name", name="uq_knowledge_folder_sibling_name"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    parent_id = Column(String(36), ForeignKey("knowledge_folders.id", ondelete="CASCADE"), index=True, nullable=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("KnowledgeFolder", remote_side=[id], back_populates="children")
    children = relationship("KnowledgeFolder", back_populates="parent", cascade="all, delete-orphan")
    assignments = relationship("KnowledgeFolderAssignment", back_populates="folder", cascade="all, delete-orphan")


class KnowledgeFolderAssignment(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - knowledge_id（类属性或 ORM 字段）：保存knowledge_id相关状态、配置或数据字段。
    - folder_id（类属性或 ORM 字段）：保存folder_id相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - folder（类属性或 ORM 字段）：保存folder相关状态、配置或数据字段。
    - knowledge（类属性或 ORM 字段）：保存knowledge相关状态、配置或数据字段。
    """
    __tablename__ = "knowledge_folder_assignments"
    __table_args__ = (
        UniqueConstraint("knowledge_id", name="uq_knowledge_folder_assignment_knowledge"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    knowledge_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    folder_id = Column(String(36), ForeignKey("knowledge_folders.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    folder = relationship("KnowledgeFolder", back_populates="assignments")
    knowledge = relationship("KnowledgeDocument", back_populates="assignments")
