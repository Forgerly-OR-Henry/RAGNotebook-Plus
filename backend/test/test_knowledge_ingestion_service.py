import asyncio

import pytest

from mvc.models.document import Document
from mvc.models.storage_object import StorageObject
from mvc.services.knowledge_ingestion_service import KnowledgeIngestionService


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content

    async def seek(self, offset):
        return None


def test_cancelled_upload_cleans_partial_knowledge_document(monkeypatch):
    class FakeStorageService:
        async def upload_bytes(self, *, kind, user_id, object_id, filename, content, mime_type):
            return StorageObject(
                id=object_id,
                backend="local",
                host="local",
                storage_uri=f"local://{kind}/{user_id}/{object_id}.md",
                storage_path=f"{kind}/{user_id}/{object_id}.md",
                original_filename=filename,
                mime_type=mime_type,
                file_ext=".md",
                checksum_sha256="hash",
                size_bytes=len(content),
            )

        async def read_object_bytes(self, storage_object):
            raise asyncio.CancelledError()

    cleanup_calls = []
    service = KnowledgeIngestionService(storage_service=FakeStorageService())

    async def fake_create_document_record(**kwargs):
        return Document(
            id=kwargs["document_id"],
            user_id=kwargs["user_id"],
            source_type="knowledge",
            title=kwargs["filename"],
            storage_object_id=kwargs["storage_object"].id,
            content_hash=kwargs["content_hash"],
            file_size=kwargs["file_size"],
            mime_type=kwargs["mime_type"],
            file_ext=".md",
            status="pending",
        )

    async def fake_cleanup_partial_document(**kwargs):
        cleanup_calls.append(kwargs)

    monkeypatch.setattr(service, "_create_document_record", fake_create_document_record)
    monkeypatch.setattr(service, "_cleanup_partial_document", fake_cleanup_partial_document)

    async def scenario():
        stream = service.upload_stream([FakeUploadFile("retry.md", b"# retry")], "user-1")
        await stream.__anext__()
        with pytest.raises(asyncio.CancelledError):
            async for _ in stream:
                pass

    asyncio.run(scenario())

    assert len(cleanup_calls) == 1
    assert cleanup_calls[0]["user_id"] == "user-1"
    assert cleanup_calls[0]["storage_object"].original_filename == "retry.md"


def test_upload_timeout_raises_reader_friendly_error():
    async def scenario():
        with pytest.raises(TimeoutError, match="写入索引超时"):
            await KnowledgeIngestionService._with_timeout(
                asyncio.sleep(1),
                timeout_seconds=0.01,
                timeout_message="写入索引超时",
            )

    asyncio.run(scenario())
