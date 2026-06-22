from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from models.chat_history import Base


class MindMap(Base):
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
