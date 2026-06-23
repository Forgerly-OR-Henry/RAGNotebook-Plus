from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class KnowledgeFolder(Base):
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
