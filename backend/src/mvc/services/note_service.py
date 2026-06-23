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
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger_handler import logger
from mvc.agent_gateway import note_ai_gateway
from mvc.models.document import Document
from mvc.services.note_index_service import NoteIndexService
from mvc.services.sources.registry import get_source_registry
from mvc.models.note import Note
from mvc.models.note_folder import NoteFolder, NoteFolderAssignment
from mvc.models.storage_object import StorageObject
from mvc.schemas import NoteCreate, NoteFolderCreate, NoteFolderResponse, NoteFolderTreeResponse, NoteFolderUpdate, NoteResponse, NoteUpdate
from mvc.services.storage_service import StorageService, get_storage_service

NOTE_IMPORT_ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".docx", ".doc"}
NOTE_IMPORT_MAX_FILE_SIZE = 20 * 1024 * 1024


class NoteImportError(ValueError):
    """Raised when an uploaded note file cannot be imported."""


class NoteFolderError(ValueError):
    """Raised when a note folder operation is invalid."""


def _safe_import_title(filename: str | None, fallback_text: str = "", prefer_content_title: bool = False) -> str:
    base_name = os.path.basename(filename or "").strip()
    stem = os.path.splitext(base_name)[0].strip()
    title = stem

    if prefer_content_title or not title:
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


def _escape_markdown_html(text: str) -> str:
    return html.escape(text.replace("\xa0", " "), quote=False)


def _plain_text_to_markdown(text: str) -> str:
    normalized = _normalize_import_text(text)
    return "\n".join(_escape_markdown_html(line.rstrip()) for line in normalized.split("\n")).strip()


def _docx_block_items(document):
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _docx_paragraph_to_markdown(paragraph) -> str:
    text = _escape_markdown_html(paragraph.text.strip())
    if not text:
        return ""

    style_name = (paragraph.style.name if paragraph.style else "").lower()
    heading_match = re.search(r"(?:heading|标题)\s*(\d+)", style_name)
    if heading_match:
        level = min(max(int(heading_match.group(1)), 1), 6)
        return f"{'#' * level} {text}"

    if "bullet" in style_name or "项目符号" in style_name:
        return f"- {text}"
    if "number" in style_name or "编号" in style_name:
        return f"1. {text}"
    if "list" in style_name or "列表" in style_name:
        return f"- {text}"

    return text


def _markdown_table_cell(text: str) -> str:
    return _escape_markdown_html(text.strip()).replace("\n", "<br>").replace("|", "\\|")


def _docx_table_to_markdown(table) -> str:
    rows = [[_markdown_table_cell(cell.text) for cell in row.cells] for row in table.rows]
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (width - len(row)) for row in rows]
    header = normalized_rows[0]
    separator = ["---"] * width
    body = normalized_rows[1:]

    table_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    table_lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(table_lines)


def _extract_docx_markdown(content: bytes) -> str:
    try:
        from docx import Document as DocxDocument
    except Exception as e:
        raise NoteImportError("当前环境缺少 Word 解析能力，请安装 python-docx 后重试") from e

    try:
        document = DocxDocument(io.BytesIO(content))
    except Exception as e:
        raise NoteImportError("Word 文件解析失败，请确认文件未损坏且为 .docx 格式") from e

    parts: list[str] = []
    for block in _docx_block_items(document):
        if hasattr(block, "rows"):
            markdown = _docx_table_to_markdown(block)
        else:
            markdown = _docx_paragraph_to_markdown(block)
        if markdown:
            parts.append(markdown)

    return "\n\n".join(parts)


def _extract_doc_markdown(content: bytes) -> str:
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
        parts: list[str] = []
        for element in elements:
            text = _escape_markdown_html(str(element).strip())
            if not text:
                continue
            category = (getattr(element, "category", "") or element.__class__.__name__).lower()
            if "title" in category or "header" in category:
                parts.append(f"## {text}")
            elif "list" in category:
                parts.append(f"- {text}")
            else:
                parts.append(text)
        return "\n\n".join(parts)
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
        note_markdown = _plain_text_to_markdown(raw_text)
    elif extension == ".docx":
        raw_text = _extract_docx_markdown(content)
        note_markdown = _normalize_import_text(raw_text)
    else:
        raw_text = _extract_doc_markdown(content)
        note_markdown = _normalize_import_text(raw_text)

    if not _normalize_import_text(raw_text):
        raise NoteImportError("文件未解析到可导入的文本内容")

    normalized_category = category.strip() if category else None
    return NoteCreate(
        title=_safe_import_title(filename, raw_text, prefer_content_title=extension == ".docx"),
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

    def _doc_to_response(
        self,
        note: Note,
        document: Document,
        storage_object: StorageObject,
        content: str,
        folder_id: str | None = None,
    ) -> NoteResponse:
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
            folder_id=folder_id,
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

    async def _get_note_folder_id(self, db: AsyncSession, user_id: str, note_id: str) -> str | None:
        result = await db.execute(
            select(NoteFolderAssignment.folder_id).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.note_id == note_id,
            )
        )
        return result.scalar_one_or_none()

    async def _folder_ids_for_notes(self, db: AsyncSession, user_id: str, note_ids: list[str]) -> dict[str, str]:
        if not note_ids:
            return {}
        result = await db.execute(
            select(NoteFolderAssignment.note_id, NoteFolderAssignment.folder_id).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.note_id.in_(note_ids),
            )
        )
        return {note_id: folder_id for note_id, folder_id in result.all()}

    async def _get_folder(self, db: AsyncSession, user_id: str, folder_id: str | None) -> NoteFolder | None:
        if not folder_id:
            return None
        result = await db.execute(
            select(NoteFolder).where(NoteFolder.id == folder_id, NoteFolder.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _ensure_folder(self, db: AsyncSession, user_id: str, folder_id: str | None) -> NoteFolder | None:
        if not folder_id:
            return None
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            raise NoteFolderError("文件夹不存在")
        return folder

    async def _sibling_name_exists(
        self,
        db: AsyncSession,
        user_id: str,
        name: str,
        parent_id: str | None,
        exclude_id: str | None = None,
    ) -> bool:
        conditions = [NoteFolder.user_id == user_id, NoteFolder.name == name]
        if parent_id:
            conditions.append(NoteFolder.parent_id == parent_id)
        else:
            conditions.append(NoteFolder.parent_id.is_(None))
        if exclude_id:
            conditions.append(NoteFolder.id != exclude_id)
        result = await db.execute(select(func.count(NoteFolder.id)).where(*conditions))
        return bool(result.scalar() or 0)

    async def _next_folder_sort_order(self, db: AsyncSession, user_id: str, parent_id: str | None) -> int:
        conditions = [NoteFolder.user_id == user_id]
        if parent_id:
            conditions.append(NoteFolder.parent_id == parent_id)
        else:
            conditions.append(NoteFolder.parent_id.is_(None))
        result = await db.execute(select(func.max(NoteFolder.sort_order)).where(*conditions))
        current = result.scalar()
        return int(current or 0) + 1

    async def _descendant_folder_ids(self, db: AsyncSession, user_id: str, folder_id: str) -> list[str]:
        result = await db.execute(select(NoteFolder.id, NoteFolder.parent_id).where(NoteFolder.user_id == user_id))
        children: dict[str | None, list[str]] = {}
        for current_id, parent_id in result.all():
            children.setdefault(parent_id, []).append(current_id)

        ordered: list[str] = []
        stack = [folder_id]
        while stack:
            current = stack.pop()
            ordered.append(current)
            stack.extend(children.get(current, []))
        return ordered

    async def _would_create_folder_cycle(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str,
        next_parent_id: str | None,
    ) -> bool:
        current_parent_id = next_parent_id
        while current_parent_id:
            if current_parent_id == folder_id:
                return True
            parent = await self._get_folder(db, user_id, current_parent_id)
            current_parent_id = parent.parent_id if parent else None
        return False

    async def _apply_note_folder_assignment(
        self,
        db: AsyncSession,
        user_id: str,
        note_id: str,
        folder_id: str | None,
    ) -> None:
        if folder_id:
            await self._ensure_folder(db, user_id, folder_id)
        await db.execute(
            delete(NoteFolderAssignment).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.note_id == note_id,
            )
        )
        if folder_id:
            db.add(
                NoteFolderAssignment(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    note_id=note_id,
                    folder_id=folder_id,
                )
            )

    @staticmethod
    def _folder_to_response(folder: NoteFolder, note_count: int, children: list[NoteFolderResponse]) -> NoteFolderResponse:
        return NoteFolderResponse(
            id=folder.id,
            user_id=folder.user_id,
            name=folder.name,
            parent_id=folder.parent_id,
            note_count=note_count,
            children=children,
            created_at=str(folder.created_at) if folder.created_at else None,
            updated_at=str(folder.updated_at) if folder.updated_at else None,
        )

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

    async def list_note_folders(self, db: AsyncSession, user_id: str) -> NoteFolderTreeResponse:
        result = await db.execute(
            select(NoteFolder).where(NoteFolder.user_id == user_id).order_by(NoteFolder.sort_order.asc(), NoteFolder.created_at.asc())
        )
        folders = list(result.scalars().all())

        count_result = await db.execute(
            select(NoteFolderAssignment.folder_id, func.count(NoteFolderAssignment.note_id))
            .where(NoteFolderAssignment.user_id == user_id)
            .group_by(NoteFolderAssignment.folder_id)
        )
        counts = {folder_id: count for folder_id, count in count_result.all()}

        total_result = await db.execute(select(func.count(Note.id)).where(Note.user_id == user_id))
        total_count = total_result.scalar() or 0

        unfiled_result = await db.execute(
            select(func.count(Note.id))
            .select_from(Note)
            .outerjoin(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            )
            .where(Note.user_id == user_id, NoteFolderAssignment.id.is_(None))
        )
        unfiled_count = unfiled_result.scalar() or 0

        by_parent: dict[str | None, list[NoteFolder]] = {}
        for folder in folders:
            by_parent.setdefault(folder.parent_id, []).append(folder)

        def build(parent_id: str | None) -> list[NoteFolderResponse]:
            return [
                self._folder_to_response(folder, int(counts.get(folder.id, 0)), build(folder.id))
                for folder in by_parent.get(parent_id, [])
            ]

        return NoteFolderTreeResponse(folders=build(None), total_count=total_count, unfiled_count=unfiled_count)

    async def create_folder(self, db: AsyncSession, user_id: str, payload: NoteFolderCreate) -> NoteFolderResponse:
        name = payload.name.strip()
        parent_id = payload.parent_id or None
        if parent_id:
            await self._ensure_folder(db, user_id, parent_id)
        if await self._sibling_name_exists(db, user_id, name, parent_id):
            raise NoteFolderError("同级文件夹已存在")

        folder = NoteFolder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            parent_id=parent_id,
            name=name,
            sort_order=await self._next_folder_sort_order(db, user_id, parent_id),
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return self._folder_to_response(folder, 0, [])

    async def update_folder(
        self,
        db: AsyncSession,
        user_id: str,
        folder_id: str,
        payload: NoteFolderUpdate,
    ) -> NoteFolderResponse | None:
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            return None

        fields = payload.model_fields_set
        next_name = payload.name.strip() if payload.name is not None else folder.name
        next_parent_id = folder.parent_id
        if "parent_id" in fields:
            next_parent_id = payload.parent_id or None
            if next_parent_id:
                await self._ensure_folder(db, user_id, next_parent_id)
            if await self._would_create_folder_cycle(db, user_id, folder_id, next_parent_id):
                raise NoteFolderError("不能把文件夹移动到自身或子文件夹下")

        if await self._sibling_name_exists(db, user_id, next_name, next_parent_id, exclude_id=folder_id):
            raise NoteFolderError("同级文件夹已存在")

        folder.name = next_name
        if "parent_id" in fields and next_parent_id != folder.parent_id:
            folder.parent_id = next_parent_id
            folder.sort_order = await self._next_folder_sort_order(db, user_id, next_parent_id)
        folder.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(folder)

        note_count = await db.scalar(
            select(func.count(NoteFolderAssignment.note_id)).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.folder_id == folder_id,
            )
        )
        return self._folder_to_response(folder, int(note_count or 0), [])

    async def delete_folder(self, db: AsyncSession, user_id: str, folder_id: str, mode: str = "unfile") -> int | None:
        folder = await self._get_folder(db, user_id, folder_id)
        if not folder:
            return None
        if mode not in {"unfile", "delete_notes"}:
            raise NoteFolderError("删除模式无效")

        folder_ids = await self._descendant_folder_ids(db, user_id, folder_id)
        result = await db.execute(
            select(NoteFolderAssignment.note_id).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.folder_id.in_(folder_ids),
            )
        )
        note_ids = [row[0] for row in result.all()]

        deleted_notes = 0
        if mode == "delete_notes":
            for note_id in note_ids:
                if await self.delete_note(db, note_id, user_id):
                    deleted_notes += 1
        else:
            await db.execute(
                delete(NoteFolderAssignment).where(
                    NoteFolderAssignment.user_id == user_id,
                    NoteFolderAssignment.folder_id.in_(folder_ids),
                )
            )

        await db.execute(delete(NoteFolder).where(NoteFolder.user_id == user_id, NoteFolder.id == folder_id))
        await db.commit()
        return deleted_notes

    async def create_note(self, db: AsyncSession, user_id: str, payload: NoteCreate) -> NoteResponse:
        """
        创建笔记：
        1. PostgreSQL 写入笔记（若用户提供了 tags/category 直接写入）
        2. 立即返回笔记 ID
        3. pgvector 向量写入后台执行
        4. 若用户未提供 tags/category，后台异步任务自动生成
        """
        if payload.folder_id:
            await self._ensure_folder(db, user_id, payload.folder_id)

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
        if payload.folder_id:
            db.add(
                NoteFolderAssignment(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    note_id=note_id,
                    folder_id=payload.folder_id,
                )
            )
        try:
            await db.commit()
        except Exception:
            await self.storage_service.delete_storage_object_data(storage_object)
            raise

        asyncio.create_task(self._upsert_note_vector(note_id, user_id, payload.title, payload.content))

        # 若用户已提供 tags/category，跳过自动标签生成
        user_provided_meta = payload.tags is not None or payload.category is not None
        if not user_provided_meta:
            asyncio.create_task(self._auto_tag_note_background(note_id, user_id, payload.content))

        return self._doc_to_response(note, document, storage_object, payload.content, payload.folder_id)

    async def import_note(
        self,
        db: AsyncSession,
        user_id: str,
        filename: str | None,
        content: bytes,
        category: str | None = None,
        folder_id: str | None = None,
    ) -> NoteResponse:
        """
        从上传文件导入笔记内容，并复用标准创建流程写入数据库和向量库。
        """
        payload = build_imported_note_payload(filename, content, category)
        payload.folder_id = folder_id
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
        if "folder_id" in payload.model_fields_set:
            await self._apply_note_folder_assignment(db, user_id, note_id, payload.folder_id)

        note.updated_at = datetime.now(timezone.utc)
        document.updated_at = note.updated_at
        await db.commit()

        # content 变更时后台同步向量，避免保存被外部嵌入服务阻塞。
        if content_changed:
            asyncio.create_task(self._refresh_note_vector(note_id, user_id, note.title, payload.content or ""))

        content = payload.content if payload.content is not None else await self._read_note_content(storage_object)
        folder_id = await self._get_note_folder_id(db, user_id, note_id)
        return self._doc_to_response(note, document, storage_object, content, folder_id)

    async def auto_tag_note(self, db: AsyncSession, note_id: str, user_id: str) -> NoteResponse | None:
        """
        同步生成当前笔记的关键词和分类，并返回更新后的笔记。
        """
        row = await self._get_note_row(db, note_id, user_id)
        if not row:
            return None
        note, document, storage_object = row
        content = await self._read_note_content(storage_object)
        source_text = "\n\n".join(part.strip() for part in (note.title, content) if part and part.strip())
        folder_id = await self._get_note_folder_id(db, user_id, note_id)
        if not source_text:
            return self._doc_to_response(note, document, storage_object, content, folder_id)

        result = await note_ai_gateway.generate_auto_tags(source_text)
        tags = [tag for tag in result.get("tags", []) if isinstance(tag, str) and tag.strip()]
        category = result.get("category") if isinstance(result.get("category"), str) else None

        note.tags = tags[:5]
        if category:
            note.category = category
        note.updated_at = datetime.now(timezone.utc)
        document.updated_at = note.updated_at
        await db.commit()

        logger.info(f"手动 AI 标签识别完成 note_id={note_id}, tags={note.tags}, category={note.category}")
        return self._doc_to_response(note, document, storage_object, content, folder_id)

    async def delete_note(self, db: AsyncSession, note_id: str, user_id: str) -> bool:
        """
        删除笔记：
        1. 删除 PostgreSQL 中的笔记
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
        folder_id = await self._get_note_folder_id(db, user_id, note_id)
        return self._doc_to_response(note, document, storage_object, content, folder_id)

    async def list_notes(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        tag: str | None = None,
        folder_id: str | None = None,
        unfiled: bool = False,
        sort_by: str = "updated_at",
    ) -> tuple[list[NoteResponse], int]:
        """
        分页查询笔记列表，支持按分类筛选和排序。tag 筛选为内存过滤。
        """
        conditions = [Note.user_id == user_id]
        if category:
            conditions.append(Note.category == category)
        if folder_id and unfiled:
            raise NoteFolderError("folder_id 与 unfiled 不能同时使用")
        if folder_id:
            await self._ensure_folder(db, user_id, folder_id)

        # 先查总数
        count_stmt = select(func.count(Note.id)).select_from(Note)
        if folder_id:
            count_stmt = count_stmt.join(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.folder_id == folder_id)
        elif unfiled:
            count_stmt = count_stmt.outerjoin(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.id.is_(None))
        count_stmt = count_stmt.where(*conditions)
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
        )
        if folder_id:
            stmt = stmt.join(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.folder_id == folder_id)
        elif unfiled:
            stmt = stmt.outerjoin(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.id.is_(None))
        stmt = (
            stmt.where(*conditions)
            .order_by(Note.is_pinned.desc(), order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()
        folder_map = await self._folder_ids_for_notes(db, user_id, [note.id for note, _, _ in rows])

        note_list = []
        for note, document, storage_object in rows:
            content = await self._read_note_content(storage_object)
            note_list.append(self._doc_to_response(note, document, storage_object, content, folder_map.get(note.id)))

        # tag 为 JSON 数组，在 Python 层面过滤
        if tag:
            note_list = [n for n in note_list if n.tags and tag in n.tags]

        return note_list, total

    async def search_notes(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = 30,
        folder_id: str | None = None,
        unfiled: bool = False,
    ) -> list[NoteResponse]:
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
        if folder_id and unfiled:
            raise NoteFolderError("folder_id 与 unfiled 不能同时使用")
        if folder_id:
            await self._ensure_folder(db, user_id, folder_id)

        stmt = (
            select(Note, Document, StorageObject)
            .join(Document, Note.document_id == Document.id)
            .join(StorageObject, Document.storage_object_id == StorageObject.id)
        )
        if folder_id:
            stmt = stmt.join(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.folder_id == folder_id)
        elif unfiled:
            stmt = stmt.outerjoin(
                NoteFolderAssignment,
                and_(NoteFolderAssignment.note_id == Note.id, NoteFolderAssignment.user_id == user_id),
            ).where(NoteFolderAssignment.id.is_(None))
        stmt = stmt.where(Note.user_id == user_id)
        result = await db.execute(stmt)
        matches: list[tuple[int, Note, Document, StorageObject, str]] = []

        for note, document, storage_object in result.all():
            content = await self._read_note_content(storage_object)
            rank = _rank_note_search_match(note, query, content)
            if rank is not None:
                matches.append((rank, note, document, storage_object, content))

        matches.sort(key=lambda item: _note_search_sort_key((item[0], item[1])))
        selected = matches[:top_k]
        folder_map = await self._folder_ids_for_notes(db, user_id, [note.id for _, note, _, _, _ in selected])
        return [
            self._doc_to_response(note, document, storage_object, content, folder_map.get(note.id))
            for _, note, document, storage_object, content in selected
        ]

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

    async def _auto_tag_note_background(self, note_id: str, user_id: str, content: str):
        """
        后台异步任务：LLM 分析笔记内容 → 生成标签和分类 → 更新 PostgreSQL。

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

    async def batch_update_folder(
        self, db: AsyncSession, user_id: str, note_ids: list[str], folder_id: str | None
    ) -> int:
        """
        批量移动笔记到文件夹。folder_id 为 None 时移回未归档。
        """
        if not note_ids:
            return 0
        if folder_id:
            await self._ensure_folder(db, user_id, folder_id)

        result = await db.execute(select(Note.id).where(Note.id.in_(note_ids), Note.user_id == user_id))
        existing_ids = [row[0] for row in result.all()]
        if not existing_ids:
            return 0

        await db.execute(
            delete(NoteFolderAssignment).where(
                NoteFolderAssignment.user_id == user_id,
                NoteFolderAssignment.note_id.in_(existing_ids),
            )
        )
        if folder_id:
            for note_id in existing_ids:
                db.add(
                    NoteFolderAssignment(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        note_id=note_id,
                        folder_id=folder_id,
                    )
                )
        await db.commit()
        return len(existing_ids)

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
