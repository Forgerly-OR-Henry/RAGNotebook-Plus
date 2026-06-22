import os

from langchain_core.documents import Document

from agent.rag.text_spliter import AsyncTextSplitter, DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DEFAULT_SEPARATORS
from utils.file_handler import (
    markdown_loader,
    markdown_loader_sync,
    pdf_loader,
    pdf_loader_sync,
    ppt_loader,
    ppt_loader_sync,
    txt_loader,
    txt_loader_sync,
    word_loader,
    word_loader_sync,
)
from utils.pdf_multimodal_loader import pdf_multimodal_loader, pdf_multimodal_loader_sync


class DocumentProcessor:
    """文档处理器"""

    def __init__(self, embed_model=None):
        self.spliter = AsyncTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            separators=DEFAULT_SEPARATORS,
            embedding_model=embed_model
        )

    async def get_file_document(
        self,
        read_path: str,
        content_hash: str = None,
        user_id: str = None,
        use_multimodal: bool = True,
    ) -> list[Document]:
        """异步加载文件"""
        lower_path = read_path.lower()
        if lower_path.endswith('.txt'):
            return await txt_loader(read_path)
        elif lower_path.endswith('.pdf'):
            if use_multimodal and content_hash and user_id:
                return await pdf_multimodal_loader(read_path, content_hash, user_id)
            # 回退到纯文本加载器（仅提取文字，无图片）
            return await pdf_loader(read_path)
        elif lower_path.endswith(('.md', '.markdown')):
            return await markdown_loader(read_path)
        elif lower_path.endswith(('.ppt', '.pptx')):
            return await ppt_loader(read_path)
        elif lower_path.endswith(('.doc', '.docx')):
            return await word_loader(read_path)
        else:
            return []

    def get_file_document_sync(
        self,
        read_path: str,
        content_hash: str = None,
        user_id: str = None,
        use_multimodal: bool = True,
    ) -> list[Document]:
        """同步加载文件（用于多线程场景）"""
        lower_path = read_path.lower()
        if lower_path.endswith('.txt'):
            return txt_loader_sync(read_path)
        elif lower_path.endswith('.pdf'):
            if use_multimodal and content_hash and user_id:
                return pdf_multimodal_loader_sync(read_path, content_hash, user_id)
            return pdf_loader_sync(read_path)
        elif lower_path.endswith(('.md', '.markdown')):
            return markdown_loader_sync(read_path)
        elif lower_path.endswith(('.ppt', '.pptx')):
            return ppt_loader_sync(read_path)
        elif lower_path.endswith(('.doc', '.docx')):
            return word_loader_sync(read_path)
        else:
            return []

    def split_documents_sync(self, documents: list[Document]) -> list[Document]:
        """同步分割文档（用于多线程场景）"""
        return self.spliter.split_documents_sync(documents)
