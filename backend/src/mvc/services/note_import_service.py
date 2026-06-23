import html
import io
import os
import re

from mvc.schemas import NoteCreate

NOTE_IMPORT_ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".docx", ".doc"}
NOTE_IMPORT_MAX_FILE_SIZE = 20 * 1024 * 1024


class NoteImportError(ValueError):
    """Raised when an uploaded note file cannot be imported."""


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
