"""
笔记服务层 —— 包含 CRUD、向量双写、异步自动标签等核心业务逻辑。
"""
import asyncio
import html
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger_handler import logger
from mvc.agent_gateway import note_ai_gateway
from mvc.models.document import Document
from mvc.services.note_index_service import NoteIndexService
from mvc.services.sources.registry import get_source_registry
from mvc.models.note import Note
from mvc.models.review_record import ReviewRecord
from mvc.models.storage_object import StorageObject
from mvc.schemas import NoteCreate, NoteResponse, NoteUpdate
from mvc.services.storage_service import StorageService, get_storage_service

# 艾宾浩斯间隔重复数组（天）
INTERVALS = [1, 2, 4, 7, 15, 30]
NOTE_IMPORT_ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".docx", ".doc"}
NOTE_IMPORT_MAX_FILE_SIZE = 20 * 1024 * 1024


class NoteImportError(ValueError):
    """Raised when an uploaded note file cannot be imported."""


def _safe_import_title(filename: str | None, fallback_text: str = "") -> str:
    base_name = os.path.basename(filename or "").strip()
    stem = os.path.splitext(base_name)[0].strip()
    title = stem

    if not title:
        for line in fallback_text.splitlines():
            cleaned = re.sub(r"^#+\s*", "", line).strip()
            if cleaned:
                title = cleaned
                break

    title = re.sub(r'[\\/:*?"<>|]+', "_", title).strip(" ._")
    return (title or "导入笔记")[:80]


def _decode_import_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _normalize_import_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document as DocxDocument
    except Exception as e:
        raise NoteImportError("当前环境缺少 Word 解析能力，请安装 python-docx 后重试") from e

    try:
        document = DocxDocument(io.BytesIO(content))
    except Exception as e:
        raise NoteImportError("Word 文件解析失败，请确认文件未损坏且为 .docx 格式") from e

    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))

    return "\n\n".join(parts)


def _extract_doc_text(content: bytes) -> str:
    try:
        from unstructured.partition.doc import partition_doc
    except Exception as e:
        raise NoteImportError("当前环境暂不支持旧版 .doc 解析，请另存为 .docx 后导入") from e

    import tempfile

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        elements = partition_doc(filename=temp_path)
        return "\n\n".join(str(element).strip() for element in elements if str(element).strip())
    except NoteImportError:
        raise
    except Exception as e:
        raise NoteImportError("旧版 Word 文件解析失败，请另存为 .docx 后导入") from e
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def build_imported_note_payload(filename: str | None, content: bytes, category: str | None = None) -> NoteCreate:
    extension = os.path.splitext(filename or "")[1].lower()
    if extension not in NOTE_IMPORT_ALLOWED_EXTENSIONS:
        supported = "、".join(sorted(NOTE_IMPORT_ALLOWED_EXTENSIONS))
        raise NoteImportError(f"文件类型不支持，目前支持 {supported}")

    if not content:
        raise NoteImportError("导入文件为空")
    if len(content) > NOTE_IMPORT_MAX_FILE_SIZE:
        raise NoteImportError("导入文件大小不能超过 20MB")

    if extension in {".md", ".markdown"}:
        raw_text = _decode_import_text(content)
        note_markdown = _normalize_import_text(raw_text)
    elif extension == ".txt":
        raw_text = _decode_import_text(content)
        note_markdown = _normalize_import_text(raw_text)
    elif extension == ".docx":
        raw_text = _extract_docx_text(content)
        note_markdown = _normalize_import_text(raw_text)
    else:
        raw_text = _extract_doc_text(content)
        note_markdown = _normalize_import_text(raw_text)

    if not _normalize_import_text(raw_text):
        raise NoteImportError("文件未解析到可导入的文本内容")

    normalized_category = category.strip() if category else None
    return NoteCreate(
        title=_safe_import_title(filename, raw_text),
        content=note_markdown,
        category=normalized_category or None,
    )


def _strip_note_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6]|tr|table)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def _normalize_search_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", _strip_note_html(value).lower()).strip()


def _compact_search_text(value: str | None) -> str:
    return re.sub(r"\s+", "", _normalize_search_text(value))


def _is_subsequence(needle: str, haystack: str) -> bool:
    if not needle:
        return False

    index = 0
    for char in haystack:
        if char == needle[index]:
            index += 1
            if index == len(needle):
                return True
    return False


def _rank_note_search_match(note: Note, query: str, content_value: str) -> int | None:
    normalized_query = _normalize_search_text(query)
    compact_query = _compact_search_text(query)
    if not compact_query:
        return None

    title = _normalize_search_text(note.title)
    compact_title = _compact_search_text(note.title)
    category = _normalize_search_text(note.category)
    compact_category = _compact_search_text(note.category)
    tags = [_normalize_search_text(tag) for tag in (note.tags or []) if isinstance(tag, str)]
    compact_tags = [_compact_search_text(tag) for tag in tags]
    content = _normalize_search_text(content_value)
    compact_content = _compact_search_text(content_value)

    if compact_title == compact_query:
        return 0
    if compact_category == compact_query or compact_query in compact_tags:
        return 1
    if normalized_query in title or compact_query in compact_title:
        return 2
    if (
        normalized_query in category
        or compact_query in compact_category
        or any(normalized_query in tag or compact_query in compact_tag for tag, compact_tag in zip(tags, compact_tags))
    ):
        return 3
    if normalized_query in content or compact_query in compact_content:
        return 4

    terms = [term for term in normalized_query.split(" ") if term]
    if len(terms) > 1:
        combined_text = " ".join([title, category, *tags, content])
        if all(term in combined_text for term in terms):
            return 5

    if _is_subsequence(compact_query, compact_title):
        return 6
    if _is_subsequence(compact_query, compact_category) or any(_is_subsequence(compact_query, tag) for tag in compact_tags):
        return 7
    if _is_subsequence(compact_query, compact_content):
        return 8

    return None


def _note_search_sort_key(match: tuple[int, Note]) -> tuple[int, int, float, str]:
    rank, note = match
    updated_at = note.updated_at or note.created_at
    if updated_at is None:
        timestamp = 0.0
    else:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        timestamp = updated_at.timestamp()

    return (
        rank,
        0 if note.is_pinned else 1,
        -timestamp,
        _normalize_search_text(note.title),
    )


def _get_next_interval(review_count: int) -> int:
    """
    根据回顾次数返回下一次回顾间隔天数。
    超出预定义数组后固定使用 30 天间隔。
    """
    if review_count < len(INTERVALS):
        return INTERVALS[review_count]
    return INTERVALS[-1]


class NoteService:
    """
    笔记服务 —— 单例模式（模块级实例 note_service）。

    职责：
    - 笔记 CRUD（PostgreSQL 存储）
    - 通过 NoteIndexService 异步同步索引
    - 异步自动标签生成（LLM 后台任务）
    """

    def __init__(self, embed_model=None, storage_service: StorageService | None = None):
        """
        初始化笔记索引服务。
        :param embed_model: 嵌入模型实例（后台初始化完成后传入）
        """
        self.index_service = NoteIndexService(embed_model=embed_model)
        self.storage_service = storage_service or get_storage_service()

    @staticmethod
    def _copy_storage_fields(target: StorageObject, source: StorageObject) -> None:
        for field in (
            "backend",
            "host",
            "protocol",
            "storage_uri",
            "storage_path",
            "original_filename",
            "mime_type",
            "file_ext",
            "checksum_sha256",
            "size_bytes",
            "status",
        ):
            setattr(target, field, getattr(source, field))

    def _doc_to_response(self, note: Note, document: Document, storage_object: StorageObject, content: str) -> NoteResponse:
        """
        将 SQLAlchemy ORM 对象转换为 Pydantic 响应模型。
        """
        return NoteResponse(
            id=note.id,
            user_id=note.user_id,
            document_id=document.id,
            title=note.title,
            content=content,
            storage_uri=storage_object.storage_uri,
            tags=note.tags if note.tags else None,
            category=note.category,
            is_pinned=note.is_pinned if note.is_pinned else False,
            created_at=str(note.created_at) if note.created_at else None,
            updated_at=str(note.updated_at) if note.updated_at else None,
        )

    async def _read_note_content(self, storage_object: StorageObject) -> str:
        try:
            return await self.storage_service.read_object_text(storage_object)
        except FileNotFoundError:
            logger.error(f"笔记文件不存在 storage_object_id={storage_object.id}")
            return ""

    async def _get_note_row(self, db: AsyncSession, note_id: str, user_id: str):
        result = await db.execute(
            select(Note, Document, StorageObject)
            .join(Document, Note.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .where(Note.id == note_id, Note.user_id == user_id)
        )
        return result.one_or_none()

    async def _upsert_note_vector(self, note_id: str, user_id: str, title: str, content: str) -> None:
        """
        后台写入单篇笔记向量。失败只影响语义检索，不影响笔记本体保存。
        """
        if not content.strip():
            return

        try:
            await self.index_service.upsert_note(note_id, user_id, title, content)
        except Exception as e:
            logger.error(f"笔记索引失败 note_id={note_id}: {e}")

    async def _refresh_note_vector(self, note_id: str, user_id: str, title: str, content: str) -> None:
        """
        后台刷新笔记向量。内容清空时只删除旧向量。
        """
        try:
            await self.index_service.refresh_note(note_id, user_id, title, content)
        except Exception as e:
            logger.error(f"更新笔记索引失败 note_id={note_id}: {e}")

    async def create_note(self, db: AsyncSession, user_id: str, payload: NoteCreate) -> NoteResponse:
        """
        创建笔记：
        1. PostgreSQL 写入笔记（若用户提供了 tags/category 直接写入）
        2. 立即返回笔记 ID
        3. pgvector 向量写入后台执行
        4. 若用户未提供 tags/category，后台异步任务自动生成
        """
        note_id = str(uuid.uuid4())
        document_id = note_id
        now = datetime.now(timezone.utc)
        content_bytes = payload.content.encode("utf-8")
        storage_object = await self.storage_service.upload_bytes(
            kind="notes",
            user_id=user_id,
            object_id=document_id,
            filename=f"{payload.title or note_id}.md",
            content=content_bytes,
            mime_type="text/markdown",
        )
        document = Document(
            id=document_id,
            user_id=user_id,
            source_type="note",
            title=payload.title,
            storage_object_id=storage_object.id,
            content_hash=storage_object.checksum_sha256,
            file_size=storage_object.size_bytes,
            mime_type="text/markdown",
            file_ext=".md",
            status="ready",
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        note = Note(
            id=note_id,
            user_id=user_id,
            document_id=document_id,
            title=payload.title,
            tags=payload.tags,
            category=payload.category,
            is_pinned=False,
            created_at=now,
            updated_at=now,
        )
        db.add(storage_object)
        db.add(document)
        db.add(note)
        try:
            await db.commit()
        except Exception:
            await self.storage_service.delete_storage_object_data(storage_object)
            raise

        asyncio.create_task(self._upsert_note_vector(note_id, user_id, payload.title, payload.content))

        # 若用户已提供 tags/category，跳过自动标签生成
        user_provided_meta = payload.tags is not None or payload.category is not None
        if not user_provided_meta:
            asyncio.create_task(self._auto_tag_and_review(note_id, user_id, payload.content))

        return self._doc_to_response(note, document, storage_object, payload.content)

    async def import_note(
        self,
        db: AsyncSession,
        user_id: str,
        filename: str | None,
        content: bytes,
        category: str | None = None,
    ) -> NoteResponse:
        """
        从上传文件导入笔记内容，并复用标准创建流程写入数据库和向量库。
        """
        payload = build_imported_note_payload(filename, content, category)
        return await self.create_note(db, user_id, payload)

    async def update_note(self, db: AsyncSession, note_id: str, user_id: str, payload: NoteUpdate) -> NoteResponse | None:
        """
        更新笔记：
        1. 更新 PostgreSQL 中的 title/content/category/tags
        2. 如果 content 变更，删除旧向量并写入新向量
        """
        row = await self._get_note_row(db, note_id, user_id)
        if not row:
            return None
        note, document, storage_object = row

        content_changed = payload.content is not None

        if payload.title is not None:
            note.title = payload.title
            document.title = payload.title
        if payload.content is not None:
            new_storage = await self.storage_service.upload_bytes(
                kind="notes",
                user_id=user_id,
                object_id=document.id,
                filename=f"{note.title or note_id}.md",
                content=payload.content.encode("utf-8"),
                mime_type="text/markdown",
            )
            self._copy_storage_fields(storage_object, new_storage)
            document.content_hash = new_storage.checksum_sha256
            document.file_size = new_storage.size_bytes
            document.mime_type = "text/markdown"
            document.file_ext = ".md"
            document.status = "ready"
            document.status_message = None
        if payload.category is not None:
            note.category = payload.category
        if payload.tags is not None:
            note.tags = payload.tags
        if payload.is_pinned is not None:
            note.is_pinned = payload.is_pinned

        note.updated_at = datetime.now(timezone.utc)
        document.updated_at = note.updated_at
        await db.commit()

        # content 变更时后台同步向量，避免保存被外部嵌入服务阻塞。
        if content_changed:
            asyncio.create_task(self._refresh_note_vector(note_id, user_id, note.title, payload.content or ""))

        content = payload.content if payload.content is not None else await self._read_note_content(storage_object)
        return self._doc_to_response(note, document, storage_object, content)

    async def delete_note(self, db: AsyncSession, note_id: str, user_id: str) -> bool:
        """
        删除笔记：
        1. 删除 PostgreSQL 中的笔记（复习计划通过 FK CASCADE 自动删除）
        2. 删除 pgvector 中的向量
        """
        row = await self._get_note_row(db, note_id, user_id)
        if not row:
            return False
        note, document, storage_object = row

        try:
            await self.storage_service.delete_storage_object_data(storage_object)
        except Exception as e:
            logger.error(f"删除笔记文件失败 note_id={note_id}: {e}")

        await db.delete(note)
        await db.delete(document)
        await db.delete(storage_object)
        await db.commit()

        # 清理索引
        try:
            await self.index_service.delete_note(note_id, user_id)
        except Exception as e:
            logger.error(f"删除笔记索引失败 note_id={note_id}: {e}")

        return True

    async def get_note(self, db: AsyncSession, note_id: str, user_id: str) -> NoteResponse | None:
        """
        根据笔记 ID 和用户 ID 获取笔记详情。
        """
        row = await self._get_note_row(db, note_id, user_id)
        if not row:
            return None
        note, document, storage_object = row
        content = await self._read_note_content(storage_object)
        return self._doc_to_response(note, document, storage_object, content)

    async def list_notes(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        tag: str | None = None,
        sort_by: str = "updated_at",
    ) -> tuple[list[NoteResponse], int]:
        """
        分页查询笔记列表，支持按分类筛选和排序。tag 筛选为内存过滤。
        """
        conditions = [Note.user_id == user_id]
        if category:
            conditions.append(Note.category == category)

        # 先查总数
        count_stmt = select(func.count(Note.id)).where(*conditions)
        result = await db.execute(count_stmt)
        total = result.scalar() or 0

        sort_column = {
            "updated_at": Note.updated_at,
            "created_at": Note.created_at,
            "title": Note.title,
        }.get(sort_by, Note.updated_at)

        if sort_by == "title":
            order = sort_column.asc()
        else:
            order = sort_column.desc()

        # 分页查询，置顶优先 + 指定排序
        stmt = (
            select(Note, Document, StorageObject)
            .join(Document, Note.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .where(*conditions)
            .order_by(Note.is_pinned.desc(), order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        note_list = []
        for note, document, storage_object in rows:
            content = await self._read_note_content(storage_object)
            note_list.append(self._doc_to_response(note, document, storage_object, content))

        # tag 为 JSON 数组，在 Python 层面过滤
        if tag:
            note_list = [n for n in note_list if n.tags and tag in n.tags]

        return note_list, total

    async def search_notes(self, db: AsyncSession, user_id: str, query: str, top_k: int = 30) -> list[NoteResponse]:
        """
        文本搜索笔记：准确匹配优先，模糊匹配在后。

        排序优先级：
        1. 标题完全匹配
        2. 分类/标签完全匹配
        3. 标题包含关键词
        4. 分类/标签包含关键词
        5. 正文包含关键词
        6. 分词匹配
        7. 字符顺序模糊匹配
        """
        if not _compact_search_text(query):
            return []

        stmt = (
            select(Note, Document, StorageObject)
            .join(Document, Note.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
            .where(Note.user_id == user_id)
        )
        result = await db.execute(stmt)
        matches: list[tuple[int, Note, Document, StorageObject, str]] = []

        for note, document, storage_object in result.all():
            content = await self._read_note_content(storage_object)
            rank = _rank_note_search_match(note, query, content)
            if rank is not None:
                matches.append((rank, note, document, storage_object, content))

        matches.sort(key=lambda item: _note_search_sort_key((item[0], item[1])))
        return [self._doc_to_response(note, document, storage_object, content) for _, note, document, storage_object, content in matches[:top_k]]

    async def get_related_notes(
        self,
        db: AsyncSession,
        note_id: str,
        user_id: str,
        top_k: int = 3,
    ) -> list[dict]:
        """
        获取与当前笔记语义相似的其他笔记和知识库文档。
        检索通过 SourceRegistry 进行，笔记服务不直接依赖知识库实现。
        """
        note = await self.get_note(db, note_id, user_id)
        if not note:
            return []

        try:
            chunks = await get_source_registry().search(db, user_id, note.content, source_type="mixed", top_k=top_k + 2)
        except Exception as e:
            logger.error(f"检索关联来源失败 note_id={note_id}: {e}")
            return []

        related_items = []
        for chunk in chunks:
            if chunk.source_type == "note" and chunk.source_id == note_id:
                continue
            related_items.append({
                "id": chunk.source_id,
                "title": chunk.title,
                "content_preview": chunk.content[:150],
                "content": chunk.content,
                "similarity": round(chunk.score or 0.0, 4),
                "source": "knowledge_base" if chunk.source_type == "knowledge" else "note",
            })
        return related_items[:top_k]

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        从 LLM 输出中提取 JSON 字符串。
        处理以下情况：
        - JSON 被 markdown 代码块包裹（```json ... ```）
        - JSON 前面有文字描述
        - JSON 后面有文字描述
        """
        import re

        # 尝试匹配 markdown 代码块中的 JSON
        match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 尝试从第一个 { 到最后一个 } 提取 JSON
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        return text

    async def _auto_tag_and_review(self, note_id: str, user_id: str, content: str):
        """
        后台异步任务：LLM 分析笔记内容 → 生成标签和分类 → 更新 PostgreSQL → 创建回顾记录。

        此方法在 create_note 结束后通过 asyncio.create_task 执行，
        不阻塞用户保存响应。标签延迟出现是设计意图。
        """
        try:
            from db.db_config import AsyncSessionLocal

            result = await note_ai_gateway.generate_auto_tags(content)
            tags = result.get("tags", [])
            category = result.get("category", "life")

            logger.info(f"自动标签生成完成 note_id={note_id}, tags={tags}, category={category}")

            # 写入 PostgreSQL
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(Note)
                    .where(Note.id == note_id, Note.user_id == user_id)
                    .values(tags=tags, category=category)
                )
                await session.execute(stmt)

                # 创建回顾记录（首次间隔 1 天）
                now = datetime.now()
                review = ReviewRecord(
                    id=str(uuid.uuid4()),
                    note_id=note_id,
                    user_id=user_id,
                    next_review_at=now + timedelta(days=1),
                    interval_days=1,
                    review_count=0,
                )
                session.add(review)
                await session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 标签输出失败 note_id={note_id}: {e}")
        except Exception as e:
            logger.error(f"自动标签后台任务失败 note_id={note_id}: {e}")

    async def autocomplete(self, context: str) -> dict:
        """
        AI 内联补全 —— 基于光标前上下文，调用 Ollama qwen3.5:0.8b 快速生成续写文本。

        Args:
            context: 光标前的文本上下文（最多 50 字）

        Returns:
            {"completion": "续写文本", "success": true/false}
        """
        return await note_ai_gateway.autocomplete(context)

    async def assist_stream(self, content: str, action: str):
        """
        AI 写作辅助 SSE 流式输出 —— 支持续写/缩写/扩写三种模式。

        Args:
            content: 用户选中的文本
            action: 操作类型 (expand / summarize / continue)

        Yields:
            SSE 事件数据（字符串）
        """
        async for event in note_ai_gateway.assist_stream(content, action):
            yield event

    async def get_category_stats(self, db: AsyncSession, user_id: str) -> dict:
        """
        获取用户的笔记分类统计 —— 动态查询所有存在的分类并计数。
        """
        stmt = select(Note.category, func.count(Note.id)).where(
            Note.user_id == user_id,
            Note.category.isnot(None),
        ).group_by(Note.category)
        result = await db.execute(stmt)
        categories = [{"category": cat, "count": count} for cat, count in result]

        count_stmt = select(func.count(Note.id)).where(
            Note.user_id == user_id,
            Note.category.is_(None),
        )
        result = await db.execute(count_stmt)
        uncategorized = result.scalar() or 0

        total_stmt = select(func.count(Note.id)).where(Note.user_id == user_id)
        result = await db.execute(total_stmt)
        total = result.scalar() or 0

        return {
            "total": total,
            "categories": categories,
            "uncategorized": uncategorized,
        }

    async def delete_category(self, db: AsyncSession, user_id: str, category: str) -> int:
        """
        删除某个分类及其下所有笔记。
        返回被删除的笔记数量。
        """
        stmt = select(Note).where(
            Note.user_id == user_id,
            Note.category == category,
        )
        result = await db.execute(stmt)
        notes = result.scalars().all()
        note_ids = [n.id for n in notes]
        if not note_ids:
            return 0

        deleted = 0
        for nid in note_ids:
            if await self.delete_note(db, nid, user_id):
                deleted += 1

        return deleted

    async def export_note_markdown(self, db: AsyncSession, note_id: str, user_id: str) -> str | None:
        """
        导出单篇笔记为 Markdown 文本。
        包含 frontmatter 格式的元数据（标题、标签、分类、日期）。
        """
        note = await self.get_note(db, note_id, user_id)
        if not note:
            return None

        lines = ["---"]
        lines.append(f"title: {note.title}")
        if note.tags:
            lines.append(f"tags: [{', '.join(note.tags)}]")
        if note.category:
            lines.append(f"category: {note.category}")
        lines.append(f"created_at: {note.created_at}")
        lines.append(f"updated_at: {note.updated_at}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {note.title}")
        lines.append("")
        lines.append(note.content)

        return "\n".join(lines)


    async def batch_delete_notes(self, db: AsyncSession, user_id: str, note_ids: list[str]) -> int:
        """
        批量删除笔记：
        1. PostgreSQL 批量删除（级联复习计划）
        2. pgvector 逐个清理向量
        返回实际删除数量。
        """
        if not note_ids:
            return 0

        stmt = select(Note).where(Note.id.in_(note_ids), Note.user_id == user_id)
        result = await db.execute(stmt)
        existing = result.scalars().all()
        existing_ids = [n.id for n in existing]

        if not existing_ids:
            return 0

        deleted = 0
        for nid in existing_ids:
            if await self.delete_note(db, nid, user_id):
                deleted += 1

        return deleted

    async def batch_update_category(
        self, db: AsyncSession, user_id: str, note_ids: list[str], category: str
    ) -> int:
        """
        批量更新笔记分类。
        返回实际更新的数量。
        """
        if not note_ids:
            return 0

        stmt = (
            update(Note)
            .where(Note.id.in_(note_ids), Note.user_id == user_id)
            .values(category=category)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def batch_export_zip(self, db: AsyncSession, user_id: str, note_ids: list[str]) -> bytes:
        """
        批量导出笔记为 ZIP 压缩包（内含 .md 文件）。
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for nid in note_ids:
                note = await self.get_note(db, nid, user_id)
                if not note:
                    continue
                md = await self.export_note_markdown(db, nid, user_id)
                if not md:
                    continue
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', note.title or nid)[:80]
                zf.writestr(f"{safe_title}.md", md.encode("utf-8"))
        buf.seek(0)
        return buf.getvalue()

    async def batch_update_pin(
        self, db: AsyncSession, user_id: str, note_ids: list[str], is_pinned: bool
    ) -> int:
        """
        批量置顶/取消置顶笔记。
        返回实际更新的数量。
        """
        if not note_ids:
            return 0

        stmt = (
            update(Note)
            .where(Note.id.in_(note_ids), Note.user_id == user_id)
            .values(is_pinned=is_pinned)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


_note_service_instance: "NoteService | None" = None


def get_note_service() -> NoteService:
    """依赖注入工厂函数。"""
    global _note_service_instance
    if _note_service_instance is None:
        from core.background_init import init_manager
        _note_service_instance = init_manager.note_service
    return _note_service_instance
