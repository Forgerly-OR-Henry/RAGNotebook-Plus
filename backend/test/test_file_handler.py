import io

import pytest

from agent.indexing.document_parser import DocumentParser
from utils.file_handler import ppt_loader_sync, word_loader_sync


def test_word_loader_sync_extracts_docx_without_unstructured(tmp_path):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("计算机体系结构", level=1)
    document.add_paragraph("流水线、缓存和指令集是核心内容")

    file_path = tmp_path / "architecture.docx"
    document.save(file_path)

    docs = word_loader_sync(str(file_path))

    assert len(docs) == 1
    assert "计算机体系结构" in docs[0].page_content
    assert "流水线、缓存和指令集" in docs[0].page_content
    assert docs[0].metadata["file_type"] == "docx"


def test_ppt_loader_sync_extracts_pptx_slides(tmp_path):
    pptx = pytest.importorskip("pptx")
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "课程结构"
    slide.placeholders[1].text = "第一章 CPU\n第二章 存储系统"

    file_path = tmp_path / "course.pptx"
    presentation.save(file_path)

    docs = ppt_loader_sync(str(file_path))

    assert len(docs) == 1
    assert "幻灯片 1" in docs[0].page_content
    assert "课程结构" in docs[0].page_content
    assert "第一章 CPU" in docs[0].page_content
    assert docs[0].metadata["slide_number"] == 1


def test_document_parser_rejects_empty_docx():
    docx = pytest.importorskip("docx")
    document = docx.Document()
    buffer = io.BytesIO()
    document.save(buffer)

    parser = DocumentParser()

    with pytest.raises(ValueError, match="未解析到可索引文本"):
        parser.parse_bytes_sync(content=buffer.getvalue(), filename="empty.docx", user_id="user-1")
