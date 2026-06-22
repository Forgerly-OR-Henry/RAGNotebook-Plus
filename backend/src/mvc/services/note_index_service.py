from __future__ import annotations

from langchain_core.documents import Document

from core.logger_handler import logger
from mvc.agent_gateway.indexing_gateway import IndexRepository


class NoteIndexService:
    def __init__(self, repository: IndexRepository | None = None, embed_model=None):
        self.repository = repository or IndexRepository(embedding_model=embed_model)

    async def upsert_note(self, note_id: str, user_id: str, title: str, content: str) -> None:
        if not content.strip():
            return
        doc = Document(
            page_content=content,
            metadata={
                "note_id": note_id,
                "document_id": note_id,
                "title": title,
                "doc_type": "note",
            },
        )
        await self.repository.upsert_documents(
            source_type="note",
            source_id=note_id,
            user_id=user_id,
            documents=[doc],
            metadata={"title": title, "note_id": note_id, "document_id": note_id},
        )

    async def refresh_note(self, note_id: str, user_id: str, title: str, content: str) -> None:
        try:
            await self.repository.delete_source(user_id=user_id, source_type="note", source_id=note_id)
            await self.upsert_note(note_id, user_id, title, content)
        except Exception as exc:
            logger.error(f"更新笔记索引失败 note_id={note_id}: {exc}")

    async def delete_note(self, note_id: str, user_id: str) -> None:
        await self.repository.delete_source(user_id=user_id, source_type="note", source_id=note_id)
