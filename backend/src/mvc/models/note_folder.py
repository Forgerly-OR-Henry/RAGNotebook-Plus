from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class NoteFolder(Base):
    __tablename__ = "note_folders"
    __table_args__ = (
        UniqueConstraint("user_id", "parent_id", "name", name="uq_note_folder_sibling_name"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    parent_id = Column(String(36), ForeignKey("note_folders.id", ondelete="CASCADE"), index=True, nullable=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("NoteFolder", remote_side=[id], back_populates="children")
    children = relationship("NoteFolder", back_populates="parent", cascade="all, delete-orphan")
    assignments = relationship("NoteFolderAssignment", back_populates="folder", cascade="all, delete-orphan")


class NoteFolderAssignment(Base):
    __tablename__ = "note_folder_assignments"
    __table_args__ = (
        UniqueConstraint("note_id", name="uq_note_folder_assignment_note"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), index=True, nullable=False)
    folder_id = Column(String(36), ForeignKey("note_folders.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    folder = relationship("NoteFolder", back_populates="assignments")
