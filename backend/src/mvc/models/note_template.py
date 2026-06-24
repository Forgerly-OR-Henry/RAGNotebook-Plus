"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from mvc.models.base import Base


class NoteTemplate(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - name（类属性或 ORM 字段）：保存name相关状态、配置或数据字段。
    - icon（类属性或 ORM 字段）：保存icon相关状态、配置或数据字段。
    - category（类属性或 ORM 字段）：保存category相关状态、配置或数据字段。
    - title（类属性或 ORM 字段）：保存title相关状态、配置或数据字段。
    - content（类属性或 ORM 字段）：保存content相关状态、配置或数据字段。
    - tags（类属性或 ORM 字段）：保存tags相关状态、配置或数据字段。
    - is_default（类属性或 ORM 字段）：保存is_default相关状态、配置或数据字段。
    - sort_order（类属性或 ORM 字段）：保存sort_order相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    """
    __tablename__ = "note_templates"

    id = Column(String(36), primary_key=True, comment="UUID")
    user_id = Column(String(36), index=True, nullable=False, comment="用户ID")
    name = Column(String(100), nullable=False, comment="模板名称")
    icon = Column(String(50), default="FileText", comment="图标名称")
    category = Column(String(50), default="", comment="默认分类")
    title = Column(String(200), default="", comment="默认标题")
    content = Column(Text, default="", comment="默认内容 Markdown")
    tags = Column(JSONB, default=list, comment="默认标签")
    is_default = Column(Boolean, default=False, nullable=False, comment="系统内置模板")
    sort_order = Column(Integer, default=0, comment="排序序号")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
