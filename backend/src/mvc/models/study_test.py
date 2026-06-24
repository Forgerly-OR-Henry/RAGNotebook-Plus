"""
模块职责：SQLAlchemy ORM 模型模块，负责声明数据库表字段和对象关系。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class StudyTestSession(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - source_type（类属性或 ORM 字段）：保存source_type相关状态、配置或数据字段。
    - source_ids（类属性或 ORM 字段）：保存source_ids相关状态、配置或数据字段。
    - question_count（类属性或 ORM 字段）：保存question_count相关状态、配置或数据字段。
    - difficulty（类属性或 ORM 字段）：保存difficulty相关状态、配置或数据字段。
    - focus（类属性或 ORM 字段）：保存focus相关状态、配置或数据字段。
    - status（类属性或 ORM 字段）：保存status相关状态、配置或数据字段。
    - current_turn（类属性或 ORM 字段）：保存current_turn相关状态、配置或数据字段。
    - summary（类属性或 ORM 字段）：保存summary相关状态、配置或数据字段。
    - weak_points（类属性或 ORM 字段）：保存weak_points相关状态、配置或数据字段。
    - recommended_refs（类属性或 ORM 字段）：保存recommended_refs相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - updated_at（类属性或 ORM 字段）：保存updated_at相关状态、配置或数据字段。
    - completed_at（类属性或 ORM 字段）：保存completed_at相关状态、配置或数据字段。
    - turns（类属性或 ORM 字段）：保存turns相关状态、配置或数据字段。
    """
    __tablename__ = "quiz_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    source_type = Column(String(20), nullable=False)
    source_ids = Column(JSONB, default=list, nullable=False)
    question_count = Column(Integer, default=5, nullable=False)
    difficulty = Column(String(20), default="normal", nullable=False)
    focus = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    current_turn = Column(Integer, default=1, nullable=False)
    summary = Column(Text, nullable=True)
    weak_points = Column(JSONB, default=list, nullable=False)
    recommended_refs = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    turns = relationship("StudyTestTurn", back_populates="session", cascade="all, delete-orphan")


class StudyTestTurn(Base):
    """
    用途：SQLAlchemy ORM 模型，用于映射数据库表和对象关系。

    属性：
    - id（类属性或 ORM 字段）：保存id相关状态、配置或数据字段。
    - session_id（类属性或 ORM 字段）：保存session_id相关状态、配置或数据字段。
    - user_id（类属性或 ORM 字段）：保存user_id相关状态、配置或数据字段。
    - turn_index（类属性或 ORM 字段）：保存turn_index相关状态、配置或数据字段。
    - question（类属性或 ORM 字段）：保存question相关状态、配置或数据字段。
    - answer（类属性或 ORM 字段）：保存answer相关状态、配置或数据字段。
    - feedback（类属性或 ORM 字段）：保存feedback相关状态、配置或数据字段。
    - score（类属性或 ORM 字段）：保存score相关状态、配置或数据字段。
    - citations（类属性或 ORM 字段）：保存citations相关状态、配置或数据字段。
    - created_at（类属性或 ORM 字段）：保存created_at相关状态、配置或数据字段。
    - session（类属性或 ORM 字段）：保存session相关状态、配置或数据字段。
    """
    __tablename__ = "quiz_turns"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), index=True, nullable=False)
    turn_index = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    citations = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("StudyTestSession", back_populates="turns")
