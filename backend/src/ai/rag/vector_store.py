from __future__ import annotations

import asyncio
import json
import math
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import text

from core.logger_handler import logger
from db.db_config import AsyncSessionLocal
from utils.image_extractor import delete_image_directory, delete_user_all_images

from .document_handler import DocumentProcessor
from .md5_manager import MD5Store


STORE_KNOWLEDGE = "knowledge"
STORE_NOTE = "note"
PUBLIC_USER_ID = "__public__"
_METADATA_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


def embedding_dimension() -> int:
    return int(os.getenv("EMBEDDING_DIM", "1024"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return dict(loaded) if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


class _LazyEmbedding(Embeddings):
    """Resolve the embedding model only when vectors are actually needed."""

    def _get_model(self):
        from core.background_init import init_manager

        model = init_manager.embed_model
        if model is None:
            raise RuntimeError("嵌入模型尚未初始化完成，请稍后重试")
        return model

    def embed_documents(self, texts):
        return self._get_model().embed_documents(texts)

    def embed_query(self, text):
        return self._get_model().embed_query(text)


class PgVectorStore:
    """Project-owned pgvector store with a small LangChain-like surface."""

    def __init__(self, store_type: str, embedding_function: Embeddings | None = None):
        self.store_type = store_type
        self.embedding_function = embedding_function or _LazyEmbedding()
        self.embedding_dim = embedding_dimension()

    def _vector_literal(self, embedding: list[float]) -> str:
        values = [float(value) for value in embedding]
        if len(values) != self.embedding_dim:
            raise ValueError(
                f"嵌入维度不匹配：数据库配置 EMBEDDING_DIM={self.embedding_dim}，"
                f"实际模型返回 {len(values)}"
            )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("嵌入向量包含非有限数值")
        return "[" + ",".join(format(value, ".9g") for value in values) + "]"

    def _normalize_metadata(self, metadata: dict[str, Any], user_id: str | None) -> dict[str, Any]:
        normalized = dict(metadata or {})
        if user_id:
            normalized["user_id"] = user_id
        normalized.setdefault("doc_type", self.store_type)
        normalized.setdefault("created_at", _utc_now_iso())
        return normalized

    def _row_user_id(self, metadata: dict[str, Any], user_id: str | None) -> str:
        return str(user_id or metadata.get("user_id") or PUBLIC_USER_ID)

    def _document_id(self, row_id: str, metadata: dict[str, Any]) -> str:
        if self.store_type == STORE_NOTE:
            return str(metadata.get("note_id") or row_id)
        return str(metadata.get("md5") or metadata.get("original_filename") or metadata.get("source") or row_id)

    async def add_documents(
        self,
        documents: list[Document],
        ids: list[str] | None = None,
        user_id: str | None = None,
    ) -> list[str]:
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        embeddings = await asyncio.to_thread(self.embedding_function.embed_documents, texts)
        if len(embeddings) != len(documents):
            raise RuntimeError(f"嵌入结果数量不匹配：documents={len(documents)}, embeddings={len(embeddings)}")

        now = _utc_now_iso()
        row_ids = ids or [str(uuid.uuid4()) for _ in documents]
        rows: list[dict[str, Any]] = []

        for row_id, doc, embedding in zip(row_ids, documents, embeddings):
            metadata = self._normalize_metadata(doc.metadata, user_id)
            metadata["updated_at"] = now
            rows.append(
                {
                    "id": str(row_id),
                    "store": self.store_type,
                    "user_id": self._row_user_id(metadata, user_id),
                    "document_id": self._document_id(str(row_id), metadata),
                    "content": doc.page_content,
                    "metadata": json.dumps(metadata, ensure_ascii=False),
                    "embedding": self._vector_literal(embedding),
                }
            )

        stmt = text(
            """
            INSERT INTO vector_chunks (id, store, user_id, document_id, content, metadata, embedding)
            VALUES (:id, :store, :user_id, :document_id, :content, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
            ON CONFLICT (id) DO UPDATE SET
                store = EXCLUDED.store,
                user_id = EXCLUDED.user_id,
                document_id = EXCLUDED.document_id,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                updated_at = now()
            """
        )
        async with AsyncSessionLocal() as session:
            for row in rows:
                await session.execute(stmt, row)
            await session.commit()

        return row_ids

    def _metadata_expr(self, key: str) -> str:
        if not _METADATA_KEY_RE.match(key):
            raise ValueError(f"不支持的 metadata filter key: {key}")
        return f"metadata ->> '{key}'"

    def _add_in_clause(self, field_expr: str, values: list[Any], params: dict[str, Any], prefix: str) -> str:
        names = []
        for index, value in enumerate(values):
            name = f"{prefix}_{index}"
            params[name] = str(value)
            names.append(f":{name}")
        return f"{field_expr} IN ({', '.join(names)})"

    def _build_filter(self, where: dict[str, Any] | None, params: dict[str, Any], prefix: str = "w") -> list[str]:
        if not where:
            return []

        clauses: list[str] = []
        for index, (key, value) in enumerate(where.items()):
            current_prefix = f"{prefix}_{index}"
            if key == "$and":
                nested = []
                for nested_index, item in enumerate(value or []):
                    nested.extend(self._build_filter(item, params, f"{current_prefix}_{nested_index}"))
                if nested:
                    clauses.append("(" + " AND ".join(nested) + ")")
                continue
            if key == "$or":
                nested_groups = []
                for nested_index, item in enumerate(value or []):
                    nested = self._build_filter(item, params, f"{current_prefix}_{nested_index}")
                    if nested:
                        nested_groups.append("(" + " AND ".join(nested) + ")")
                if nested_groups:
                    clauses.append("(" + " OR ".join(nested_groups) + ")")
                continue

            if key == "user_id":
                field_expr = "user_id"
            elif key == "id":
                field_expr = "id"
            elif key == "document_id":
                field_expr = "document_id"
            else:
                field_expr = self._metadata_expr(key)

            if isinstance(value, dict):
                if "$in" in value:
                    clauses.append(self._add_in_clause(field_expr, value["$in"], params, current_prefix))
                elif "$eq" in value:
                    params[current_prefix] = str(value["$eq"])
                    clauses.append(f"{field_expr} = :{current_prefix}")
                elif "$ne" in value:
                    params[current_prefix] = str(value["$ne"])
                    clauses.append(f"{field_expr} <> :{current_prefix}")
                else:
                    raise ValueError(f"不支持的 metadata filter operator: {value}")
            else:
                params[current_prefix] = str(value)
                clauses.append(f"{field_expr} = :{current_prefix}")

        return clauses

    def _where_sql(self, where: dict[str, Any] | None, params: dict[str, Any]) -> str:
        clauses = ["store = :store"]
        params["store"] = self.store_type
        clauses.extend(self._build_filter(where, params))
        return " AND ".join(clauses)

    async def get(self, include: list[str] | None = None, where: dict[str, Any] | None = None) -> dict[str, list[Any]]:
        params: dict[str, Any] = {}
        where_sql = self._where_sql(where, params)
        stmt = text(
            f"""
            SELECT id, content, metadata, created_at
            FROM vector_chunks
            WHERE {where_sql}
            ORDER BY created_at ASC, id ASC
            """
        )

        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, params)
            rows = result.mappings().all()

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for row in rows:
            metadata = _metadata_dict(row["metadata"])
            metadata.setdefault("created_at", row["created_at"].isoformat() if row["created_at"] else None)
            ids.append(row["id"])
            documents.append(row["content"])
            metadatas.append(metadata)

        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    async def delete(self, ids: list[str] | None = None, where: dict[str, Any] | None = None) -> int:
        if ids is not None and not ids:
            return 0

        params: dict[str, Any] = {}
        clauses = [self._where_sql(where, params)]
        if ids:
            clauses.append(self._add_in_clause("id", ids, params, "delete_id"))

        stmt = text(f"DELETE FROM vector_chunks WHERE {' AND '.join(clauses)}")
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, params)
            await session.commit()
            return result.rowcount or 0

    async def delete_by_filename(self, user_id: str, filename: str) -> int:
        stmt = text(
            """
            DELETE FROM vector_chunks
            WHERE store = :store
              AND user_id = :user_id
              AND (
                metadata ->> 'original_filename' = :filename
                OR metadata ->> 'filename' = :filename
                OR metadata ->> 'source' = :filename
              )
            """
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, {"store": self.store_type, "user_id": user_id, "filename": filename})
            await session.commit()
            return result.rowcount or 0

    async def similarity_search(self, query: str, k: int = 4, filter: dict[str, Any] | None = None) -> list[Document]:
        results = await self.similarity_search_with_score(query, k=k, filter=filter)
        return [doc for doc, _ in results]

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        query_embedding = await asyncio.to_thread(self.embedding_function.embed_query, query)
        params: dict[str, Any] = {
            "query_embedding": self._vector_literal(query_embedding),
            "limit": k,
        }
        where_sql = self._where_sql(filter, params)
        stmt = text(
            f"""
            SELECT id, content, metadata, embedding <=> CAST(:query_embedding AS vector) AS distance
            FROM vector_chunks
            WHERE {where_sql}
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
            """
        )

        async with AsyncSessionLocal() as session:
            result = await session.execute(stmt, params)
            rows = result.mappings().all()

        matches: list[tuple[Document, float]] = []
        for row in rows:
            metadata = _metadata_dict(row["metadata"])
            metadata.setdefault("chunk_id", row["id"])
            matches.append((Document(page_content=row["content"], metadata=metadata), float(row["distance"])))
        return matches


class VectorStoreService:
    """Knowledge-base vector service backed by PostgreSQL pgvector."""

    _instance = None
    _initialized = False
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if VectorStoreService._initialized:
            return

        with VectorStoreService._init_lock:
            if VectorStoreService._initialized:
                return

            self.knowledge_store = PgVectorStore(STORE_KNOWLEDGE, self._get_embed_model())
            self.md5_store = MD5Store()

            from .retrievers.hybrid_retriever import HybridRetriever

            self.hybrid_retriever = HybridRetriever(self.knowledge_store)
            self.document_processor = DocumentProcessor(self.knowledge_store, self.md5_store, self._get_embed_model())
            VectorStoreService._initialized = True

    @staticmethod
    def _get_embed_model():
        return _LazyEmbedding()

    async def add_documents(self, documents: list[Document], ids: list[str] | None = None, user_id: str | None = None) -> list[str]:
        return await self.knowledge_store.add_documents(documents, ids=ids, user_id=user_id)

    async def similarity_search_with_score(self, query: str, user_id: str, k: int = 4) -> list[tuple[Document, float]]:
        return await self.knowledge_store.similarity_search_with_score(query, k=k, filter={"user_id": user_id})

    async def get_bm25_retriever(self, user_id: str = None):
        return await self.hybrid_retriever.get_bm25_retriever(user_id)

    async def _get_all_documents(self) -> list[Document]:
        return await self.hybrid_retriever._get_all_documents()

    async def get_retriever(self, query: str = None, user_id: str = None):
        return await self.hybrid_retriever.get_retriever(query, user_id)

    @staticmethod
    async def get_dynamic_weights(query: str = None):
        from .retrievers.hybrid_retriever import HybridRetriever

        return await HybridRetriever.get_dynamic_weights(query)

    async def check_md5_hex(self, md5_for_check: str, user_id: str = None) -> bool:
        return await self.md5_store.check_md5_hex(md5_for_check, user_id)

    async def save_md5_hex(self, md5_hex: str, filename: str = None, original_filename: str = None, user_id: str = None):
        await self.md5_store.save_md5_hex(md5_hex, filename, original_filename, user_id)

    def save_md5_hex_sync(self, md5_hex: str, filename: str = None, original_filename: str = None, user_id: str = None):
        self.md5_store.save_md5_hex_sync(md5_hex, filename, original_filename, user_id)

    async def delete_user_documents(self, user_id: str):
        try:
            await self.delete_user_md5(user_id, delete_documents=True)
        except Exception as e:
            logger.error(f"【向量数据库】删除用户 {user_id} 的文档时出错: {e}")
            raise

    async def delete_user_md5(self, user_id: str, delete_documents: bool = True):
        try:
            if delete_documents:
                await self.knowledge_store.delete(where={"user_id": user_id})
                logger.info(f"【向量数据库】已删除用户 {user_id} 的所有文档")

            await self.md5_store.delete_user_md5(user_id)
            delete_user_all_images(user_id)
        except Exception as e:
            logger.error(f"【向量数据库】删除用户 {user_id} 的MD5记录时出错: {e}")

    async def delete_by_filename(self, user_id: str, filename: str, delete_documents: bool = True):
        try:
            md5_to_delete = await self.md5_store.delete_by_filename(user_id, filename)
            if md5_to_delete is None:
                logger.warning(f"【向量数据库】文件 {filename} 不存在于用户 {user_id} 的MD5记录中")
                return False

            if delete_documents:
                await self.knowledge_store.delete_by_filename(user_id, filename)
                logger.info(f"【向量数据库】已删除用户 {user_id} 中文件 {filename} 对应的文档")

            delete_image_directory(user_id, md5_to_delete)
            return True

        except Exception as e:
            logger.error(f"【向量数据库】删除用户 {user_id} 的文件 {filename} 时出错: {e}")
            return False

    async def delete_single_md5(self, user_id: str, md5_to_delete: str, delete_documents: bool = True):
        try:
            success = await self.md5_store.delete_single_md5(user_id, md5_to_delete)
            if not success:
                logger.warning(f"【向量数据库】MD5记录 {md5_to_delete} 不存在")
                return False

            if delete_documents:
                await self.knowledge_store.delete(where={"$and": [{"user_id": user_id}, {"md5": md5_to_delete}]})
                logger.info(f"【向量数据库】已删除用户 {user_id} 中MD5为 {md5_to_delete} 的文档")

            delete_image_directory(user_id, md5_to_delete)
            return True

        except Exception as e:
            logger.error(f"【向量数据库】删除用户 {user_id} 的MD5记录 {md5_to_delete} 时出错: {e}")
            return False

    async def get_md5_info(self, user_id: str, md5_value: str):
        try:
            return await self.md5_store.get_md5_info(user_id, md5_value)
        except Exception as e:
            logger.error(f"【向量数据库】获取MD5信息 {md5_value} 时出错: {e}")
            return None

    async def get_all_md5_records(self, user_id: str):
        try:
            records = await self.md5_store.get_all_md5_records(user_id)
            logger.info(f"【向量数据库】获取用户 {user_id} 的MD5记录，共 {len(records)} 条")
            return records
        except Exception as e:
            logger.error(f"【向量数据库】获取用户 {user_id} 的MD5记录时出错: {e}")
            return []

    async def _get_user_raw_docs(self, user_id: str | None = None) -> dict[str, list[Any]]:
        where_clause = {"user_id": user_id} if user_id else None
        return await self.knowledge_store.get(include=["documents", "metadatas"], where=where_clause)

    async def get_user_documents(self, user_id: str = None):
        try:
            all_docs = await self._get_user_raw_docs(user_id)
            docs_info = {}

            for i, doc_id in enumerate(all_docs["ids"]):
                metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
                content = all_docs["documents"][i] if i < len(all_docs["documents"]) else ""

                source = metadata.get("source", metadata.get("filename", "unknown"))
                if isinstance(source, str) and ("\\" in source or "/" in source):
                    source = os.path.basename(source)
                filename = metadata.get("original_filename", source)
                original_filename = metadata.get("original_filename", filename)

                if filename not in docs_info:
                    docs_info[filename] = {
                        "id": doc_id,
                        "filename": filename,
                        "original_filename": original_filename,
                        "user_id": metadata.get("user_id"),
                        "chunk_count": 0,
                        "preview": "",
                        "created_at": metadata.get("created_at"),
                    }

                docs_info[filename]["chunk_count"] += 1

                if not docs_info[filename]["preview"] and content:
                    preview_length = 100
                    docs_info[filename]["preview"] = content[:preview_length] + ("..." if len(content) > preview_length else "")

            result = list(docs_info.values())
            logger.info(f"【向量数据库】获取用户 {user_id} 的知识库文档，共 {len(result)} 个文件")
            return result

        except Exception as e:
            logger.error(f"【向量数据库】获取用户 {user_id} 的知识库文档时出错: {e}")
            raise

    async def get_document_detail(self, user_id: str, filename: str):
        try:
            all_docs = await self._get_user_raw_docs(user_id)
            doc_info = None
            full_content = []
            chunk_count = 0
            all_images = set()
            doc_md5 = None
            chunks = []

            for i, doc_id in enumerate(all_docs["ids"]):
                metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
                content = all_docs["documents"][i] if i < len(all_docs["documents"]) else ""

                source = metadata.get("source", metadata.get("filename", ""))
                source_name = os.path.basename(source) if isinstance(source, str) else str(source)
                original_filename = metadata.get("original_filename", "")

                if source_name == filename or original_filename == filename:
                    if not doc_info:
                        doc_info = {
                            "id": doc_id,
                            "filename": filename,
                            "user_id": metadata.get("user_id"),
                            "chunk_count": 0,
                            "content": "",
                            "images": [],
                            "md5": metadata.get("md5"),
                            "created_at": metadata.get("created_at"),
                        }
                        doc_md5 = metadata.get("md5")
                    chunk_count += 1
                    full_content.append(content)

                    image_paths = metadata.get("image_paths", [])
                    chunk_images = []
                    if isinstance(image_paths, list):
                        for img_name in image_paths:
                            img_url = f"/knowledge/image/{doc_md5}/{img_name}"
                            all_images.add(img_url)
                            chunk_images.append(img_url)

                    chunks.append(
                        {
                            "chunk_id": doc_id,
                            "index": len(chunks),
                            "content": content,
                            "page": metadata.get("page"),
                            "images": chunk_images,
                        }
                    )

            if doc_info:
                doc_info["chunk_count"] = chunk_count
                doc_info["content"] = "\n".join(full_content)
                doc_info["images"] = sorted(all_images)
                doc_info["chunks"] = chunks

            logger.info(f"【向量数据库】获取文档详情: {filename}，chunk数量: {chunk_count}，图片数量: {len(all_images)}")
            return doc_info

        except Exception as e:
            logger.error(f"【向量数据库】获取文档详情 {filename} 时出错: {e}")
            raise

    async def get_document_chunks(self, user_id: str, filename: str):
        try:
            all_docs = await self._get_user_raw_docs(user_id)
            chunks = []
            chunk_index = 0

            for i, doc_id in enumerate(all_docs["ids"]):
                metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
                content = all_docs["documents"][i] if i < len(all_docs["documents"]) else ""

                source = metadata.get("source", metadata.get("filename", ""))
                source_name = os.path.basename(source) if isinstance(source, str) else str(source)
                original_filename = metadata.get("original_filename", "")

                if source_name == filename or original_filename == filename:
                    doc_md5 = metadata.get("md5", "")
                    image_paths = metadata.get("image_paths", [])
                    images = [f"/knowledge/image/{doc_md5}/{img}" for img in image_paths] if isinstance(image_paths, list) else []

                    chunks.append(
                        {
                            "chunk_id": doc_id,
                            "index": chunk_index,
                            "content": content,
                            "metadata": metadata,
                            "images": images,
                        }
                    )
                    chunk_index += 1

            result = {"filename": filename, "total_chunks": len(chunks), "chunks": chunks}
            logger.info(f"【向量数据库】获取文档切片: {filename}，共 {len(chunks)} 个切片")
            return result

        except Exception as e:
            logger.error(f"【向量数据库】获取文档切片 {filename} 时出错: {e}")
            raise

    async def get_file_document(
        self,
        read_path: str,
        md5: str = None,
        user_id: str = None,
        use_multimodal: bool = True,
    ) -> list[Document]:
        return await self.document_processor.get_file_document(read_path, md5, user_id, use_multimodal=use_multimodal)

    def get_file_document_sync(
        self,
        read_path: str,
        md5: str = None,
        user_id: str = None,
        use_multimodal: bool = True,
    ) -> list[Document]:
        return self.document_processor.get_file_document_sync(read_path, md5, user_id, use_multimodal=use_multimodal)

    def split_documents_sync(self, documents: list[Document]) -> list[Document]:
        return self.document_processor.split_documents_sync(documents)

    async def get_document(self, files: list = None, user_id: str = None, progress_callback=None):
        await self.document_processor.get_document(files, user_id, progress_callback)
