from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass

from langchain_core.documents import Document

from agent.rag.document_handler.processor import DocumentProcessor


@dataclass
class ParsedDocument:
    content_hash: str
    documents: list[Document]


class DocumentParser:
    """File parsing and chunking adapter independent of vector persistence."""

    def __init__(self, embed_model=None):
        self.processor = DocumentProcessor(embed_model=embed_model)

    def parse_bytes_sync(
        self,
        *,
        content: bytes,
        filename: str,
        user_id: str,
        use_multimodal: bool = False,
    ) -> ParsedDocument:
        suffix = os.path.splitext(filename or "")[1]
        content_hash = hashlib.sha256(content).hexdigest()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                handle.write(content)
                temp_path = handle.name

            documents = self.processor.get_file_document_sync(
                temp_path,
                content_hash=content_hash,
                user_id=user_id,
                use_multimodal=use_multimodal,
            )
            split_docs = self.processor.split_documents_sync(documents) if documents else []
            return ParsedDocument(content_hash=content_hash, documents=split_docs)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
