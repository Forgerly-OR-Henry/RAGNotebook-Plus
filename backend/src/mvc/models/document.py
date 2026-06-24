"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class Document(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - source_type（类属性或 ORM 字段）：保存source_type相关状态、配置或数据字段。
    - title（类属性或 ORM 字段）：保存title相关状态、配置或数据字段。
    - storage_object_id（类属性或 ORM 字段）：保存storage_object_id相关状态、配置或数据字段。
    - content_hash（类属性或 ORM 字段）：保存content_hash相关状态、配置或数据字段。
    - file_size（类属性或 ORM 字段）：保存file_size相关状态、配置或数据字段。
    - mime_type（类属性或 ORM 字段）：保存mime_type相关状态、配置或数据字段。
    - file_ext（类属性或 ORM 字段）：保存file_ext相关状态、配置或数据字段。
    - status（类属性或 ORM 字段）：保存status相关状态、配置或数据字段。
    - status_message（类属性或 ORM 字段）：保存status_message相关状态、配置或数据字段。
    - chunk_count（类属性或 ORM 字段）：保存chunk_count相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - storage_object（类属性或 ORM 字段）：保存storage_object相关状态、配置或数据字段。
    - note（类属性或 ORM 字段）：保存note相关状态、配置或数据字段。
    - knowledge_document（类属性或 ORM 字段）：保存knowledge_document相关状态、配置或数据字段。
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    source_type = Column(String(20), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    storage_object_id = Column(String(36), ForeignKey("storage_objects.id"), nullable=False)
    content_hash = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(120), nullable=True)
    file_ext = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    status_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    storage_object = relationship("StorageObject")
    note = relationship("Note", back_populates="document", uselist=False)
    knowledge_document = relationship("KnowledgeDocument", back_populates="document", uselist=False)
