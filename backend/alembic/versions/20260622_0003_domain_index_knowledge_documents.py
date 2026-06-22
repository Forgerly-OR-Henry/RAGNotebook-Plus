"""domain index and knowledge documents

Revision ID: 20260622_0003
Revises: 20260621_0002
Create Date: 2026-06-22
"""

from __future__ import annotations

import os

from alembic import op


revision = "20260622_0003"
down_revision = "20260621_0002"
branch_labels = None
depends_on = None


def _embedding_dim() -> int:
    return int(os.getenv("EMBEDDING_DIM", "1024"))


def upgrade() -> None:
    embedding_dim = _embedding_dim()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            md5 VARCHAR(32) NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            mime_type VARCHAR(120),
            status VARCHAR(30) NOT NULL DEFAULT 'processing',
            status_message TEXT,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_knowledge_documents_user_md5 UNIQUE (user_id, md5)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_documents_user ON knowledge_documents (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_documents_status ON knowledge_documents (user_id, status)")

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS index_chunks (
            id VARCHAR(64) PRIMARY KEY,
            source_type VARCHAR(32) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            embedding vector({embedding_dim}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_index_chunks_source ON index_chunks (source_type, user_id, source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_index_chunks_metadata ON index_chunks USING gin (metadata jsonb_path_ops)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_index_chunks_embedding_hnsw
        ON index_chunks USING hnsw (embedding vector_cosine_ops)
        """
    )

    op.execute(
        """
        INSERT INTO knowledge_documents (id, user_id, filename, original_filename, md5, status, status_message, chunk_count, created_at, updated_at)
        SELECT
            gen_random_uuid()::text AS id,
            vc.user_id,
            COALESCE(vc.metadata ->> 'filename', vc.metadata ->> 'original_filename', vc.metadata ->> 'source', vc.document_id, 'unknown') AS filename,
            COALESCE(vc.metadata ->> 'original_filename', vc.metadata ->> 'filename', vc.metadata ->> 'source', vc.document_id, 'unknown') AS original_filename,
            COALESCE(vc.metadata ->> 'md5', md5(COALESCE(vc.document_id, vc.id))) AS md5,
            CASE WHEN COUNT(*) FILTER (WHERE vc.embedding IS NULL) > 0 THEN 'needs_reindex' ELSE 'ready' END AS status,
            CASE WHEN COUNT(*) FILTER (WHERE vc.embedding IS NULL) > 0 THEN '旧切片缺少可迁移向量，需重新上传或重建索引' ELSE NULL END AS status_message,
            COUNT(*)::integer AS chunk_count,
            MIN(vc.created_at),
            MAX(vc.updated_at)
        FROM vector_chunks vc
        WHERE vc.store = 'knowledge'
        GROUP BY vc.user_id, COALESCE(vc.metadata ->> 'md5', md5(COALESCE(vc.document_id, vc.id))), COALESCE(vc.metadata ->> 'filename', vc.metadata ->> 'original_filename', vc.metadata ->> 'source', vc.document_id, 'unknown'), COALESCE(vc.metadata ->> 'original_filename', vc.metadata ->> 'filename', vc.metadata ->> 'source', vc.document_id, 'unknown')
        ON CONFLICT (user_id, md5) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO index_chunks (id, source_type, source_id, user_id, chunk_index, content, metadata, embedding, created_at, updated_at)
        SELECT
            vc.id,
            CASE WHEN vc.store = 'knowledge' THEN 'knowledge' ELSE 'note' END AS source_type,
            CASE
                WHEN vc.store = 'knowledge' THEN COALESCE(kd.id, vc.document_id, vc.id)
                ELSE COALESCE(vc.metadata ->> 'note_id', vc.document_id, vc.id)
            END AS source_id,
            vc.user_id,
            row_number() OVER (PARTITION BY vc.store, vc.user_id, vc.document_id ORDER BY vc.created_at, vc.id) - 1 AS chunk_index,
            vc.content,
            vc.metadata || jsonb_build_object(
                'source_type', CASE WHEN vc.store = 'knowledge' THEN 'knowledge' ELSE 'note' END,
                'source_id', CASE
                    WHEN vc.store = 'knowledge' THEN COALESCE(kd.id, vc.document_id, vc.id)
                    ELSE COALESCE(vc.metadata ->> 'note_id', vc.document_id, vc.id)
                END
            ),
            vc.embedding,
            vc.created_at,
            vc.updated_at
        FROM vector_chunks vc
        LEFT JOIN knowledge_documents kd
          ON kd.user_id = vc.user_id
         AND kd.md5 = COALESCE(vc.metadata ->> 'md5', md5(COALESCE(vc.document_id, vc.id)))
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_index_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_index_chunks_metadata")
    op.execute("DROP INDEX IF EXISTS ix_index_chunks_source")
    op.execute("DROP TABLE IF EXISTS index_chunks")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_documents_status")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_documents_user")
    op.execute("DROP TABLE IF EXISTS knowledge_documents")
