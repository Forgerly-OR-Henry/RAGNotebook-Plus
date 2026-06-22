from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from mvc.models.base import Base


class StudyTestSession(Base):
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
