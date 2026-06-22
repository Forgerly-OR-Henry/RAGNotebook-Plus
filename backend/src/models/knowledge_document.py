from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from models.chat_history import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "md5", name="uq_knowledge_documents_user_md5"),
    )

    id = Column(String(36), primary_key=True, comment="稳定文档ID")
    user_id = Column(String(36), index=True, nullable=False, comment="用户ID")
    filename = Column(Text, nullable=False, comment="存储/上传文件名")
    original_filename = Column(Text, nullable=False, comment="用户可见原始文件名")
    md5 = Column(String(32), nullable=False, comment="文件MD5")
    file_size = Column(Integer, default=0, nullable=False, comment="文件大小，字节")
    mime_type = Column(String(120), comment="MIME类型")
    status = Column(String(30), default="processing", nullable=False, comment="processing/ready/failed/needs_reindex")
    status_message = Column(Text, comment="状态说明或错误信息")
    chunk_count = Column(Integer, default=0, nullable=False, comment="切片数量")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
