from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class ChatProject(Base):
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
