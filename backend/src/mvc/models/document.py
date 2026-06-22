from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class Document(Base):
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
