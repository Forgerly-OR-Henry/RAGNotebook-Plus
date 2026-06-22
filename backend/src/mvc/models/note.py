from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, comment="UUID")
    user_id = Column(String(36), index=True, nullable=False, comment="用户ID")
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False, comment="内容文档ID")
    title = Column(String(200), nullable=False, comment="笔记标题")
    tags = Column(JSONB, comment='标签列表 ["AI", "FastAPI"]')
    category = Column(String(50), comment="分类 work/study/life/project")
    is_pinned = Column(Boolean, default=False, nullable=False, comment="是否置顶")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    document = relationship("Document", back_populates="note", uselist=False)
