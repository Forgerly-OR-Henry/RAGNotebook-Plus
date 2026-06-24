"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from mvc.models.base import Base


class StorageObject(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - backend（类属性或 ORM 字段）：保存backend相关状态、配置或数据字段。
    - host（类属性或 ORM 字段）：保存host相关状态、配置或数据字段。
    - protocol（类属性或 ORM 字段）：保存protocol相关状态、配置或数据字段。
    - storage_uri（类属性或 ORM 字段）：保存storage_uri相关状态、配置或数据字段。
    - storage_path（类属性或 ORM 字段）：保存storage_path相关状态、配置或数据字段。
    - original_filename（类属性或 ORM 字段）：保存original_filename相关状态、配置或数据字段。
    - mime_type（类属性或 ORM 字段）：保存mime_type相关状态、配置或数据字段。
    - file_ext（类属性或 ORM 字段）：保存file_ext相关状态、配置或数据字段。
    - checksum_sha256（类属性或 ORM 字段）：保存checksum_sha256相关状态、配置或数据字段。
    - size_bytes（类属性或 ORM 字段）：保存size_bytes相关状态、配置或数据字段。
    - status（类属性或 ORM 字段）：保存status相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    """
    __tablename__ = "storage_objects"

    id = Column(String(36), primary_key=True)
    backend = Column(String(20), nullable=False)
    host = Column(String(255), nullable=False)
    protocol = Column(String(20), nullable=True)
    storage_uri = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=True)
    mime_type = Column(String(120), nullable=True)
    file_ext = Column(String(20), nullable=True)
    checksum_sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="uploaded")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
