from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from mvc.models.base import Base


class StorageObject(Base):
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
