import asyncio

from langchain_core.documents import Document

from agent.rag.document_handler import processor as processor_module
from agent.rag.document_handler.processor import DocumentProcessor


def test_pdf_upload_loader_skips_multimodal_when_disabled(monkeypatch):
    calls = []

    async def fake_pdf_loader(path):
        calls.append(("plain", path))
        return [Document(page_content="plain pdf")]

    async def fake_multimodal_loader(path, content_hash, user_id):
        calls.append(("multimodal", path, content_hash, user_id))
        return [Document(page_content="vision pdf")]

    monkeypatch.setattr(processor_module, "pdf_loader", fake_pdf_loader)
    monkeypatch.setattr(processor_module, "pdf_multimodal_loader", fake_multimodal_loader)

    processor = DocumentProcessor.__new__(DocumentProcessor)
    result = asyncio.run(
        processor.get_file_document(
            "lecture.pdf",
            content_hash="hash-1",
            user_id="user-1",
            use_multimodal=False,
        )
    )

    assert result[0].page_content == "plain pdf"
    assert calls == [("plain", "lecture.pdf")]


def test_pdf_loader_keeps_multimodal_path_when_enabled(monkeypatch):
    calls = []

    async def fake_pdf_loader(path):
        calls.append(("plain", path))
        return [Document(page_content="plain pdf")]

    async def fake_multimodal_loader(path, content_hash, user_id):
        calls.append(("multimodal", path, content_hash, user_id))
        return [Document(page_content="vision pdf")]

    monkeypatch.setattr(processor_module, "pdf_loader", fake_pdf_loader)
    monkeypatch.setattr(processor_module, "pdf_multimodal_loader", fake_multimodal_loader)

    processor = DocumentProcessor.__new__(DocumentProcessor)
    result = asyncio.run(
        processor.get_file_document(
            "lecture.pdf",
            content_hash="hash-1",
            user_id="user-1",
            use_multimodal=True,
        )
    )

    assert result[0].page_content == "vision pdf"
    assert calls == [("multimodal", "lecture.pdf", "hash-1", "user-1")]
