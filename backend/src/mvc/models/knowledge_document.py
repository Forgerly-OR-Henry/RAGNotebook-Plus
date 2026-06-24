"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class KnowledgeDocument(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - document_id（类属性或 ORM 字段）：保存document_id相关状态、配置或数据字段。
    - title（类属性或 ORM 字段）：保存title相关状态、配置或数据字段。
    - category（类属性或 ORM 字段）：保存category相关状态、配置或数据字段。
    - tags（类属性或 ORM 字段）：保存tags相关状态、配置或数据字段。
    - is_pinned（类属性或 ORM 字段）：保存is_pinned相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - document（类属性或 ORM 字段）：保存document相关状态、配置或数据字段。
    - assignments（类属性或 ORM 字段）：保存assignments相关状态、配置或数据字段。
    """
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    category = Column(String(50), nullable=True)
    tags = Column(JSONB, nullable=True)
    is_pinned = Column(Boolean, default=False, nullable=False, comment="是否置顶")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document = relationship("Document", back_populates="knowledge_document")
    assignments = relationship("KnowledgeFolderAssignment", back_populates="knowledge", cascade="all, delete-orphan")
