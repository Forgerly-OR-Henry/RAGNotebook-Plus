"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from mvc.models.base import Base


class MindMap(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - title（类属性或 ORM 字段）：保存title相关状态、配置或数据字段。
    - source_type（类属性或 ORM 字段）：保存source_type相关状态、配置或数据字段。
    - source_ids（类属性或 ORM 字段）：保存source_ids相关状态、配置或数据字段。
    - focus（类属性或 ORM 字段）：保存focus相关状态、配置或数据字段。
    - graph（类属性或 ORM 字段）：保存graph相关状态、配置或数据字段。
    - citations（类属性或 ORM 字段）：保存citations相关状态、配置或数据字段。
    - source_refs（类属性或 ORM 字段）：保存source_refs相关状态、配置或数据字段。
    - model_config（类属性或 ORM 字段）：保存model_config相关状态、配置或数据字段。
    - version（类属性或 ORM 字段）：保存version相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    """
    __tablename__ = "mind_maps"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    source_type = Column(String(20), nullable=False)
    source_ids = Column(JSONB, default=list, nullable=False)
    focus = Column(Text, nullable=True)
    graph = Column(JSONB, default=dict, nullable=False)
    citations = Column(JSONB, default=list, nullable=False)
    source_refs = Column(JSONB, default=list, nullable=False)
    model_config = Column(JSONB, default=dict, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
