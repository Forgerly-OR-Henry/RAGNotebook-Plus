from __future__ import annotations

from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from ai.rag.vector_store import PgVectorStore
from utils.config import vector_config

from .empty_retriever import EmptyRetriever


class PgVectorRetriever(BaseRetriever):
    """LangChain retriever adapter for the project-owned pgvector store."""

    vector_store: PgVectorStore
    search_kwargs: dict = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        return await self.vector_store.similarity_search(
            query,
            k=self.search_kwargs.get("k", vector_config["k"]),
            filter=self.search_kwargs.get("filter"),
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        raise RuntimeError("PgVectorRetriever 仅支持异步检索，请使用 ainvoke")


class HybridRetriever:
    """混合检索器（BM25 + pgvector）"""

    def __init__(self, vector_store: PgVectorStore):
        self.vector_store = vector_store

    async def get_bm25_retriever(self, user_id: str = None):
        if not user_id:
            return None

        all_docs_result = await self.vector_store.get(
            include=["documents", "metadatas"],
            where={"user_id": user_id},
        )
        documents = []
        for i, doc_content in enumerate(all_docs_result["documents"]):
            metadata = all_docs_result["metadatas"][i] if i < len(all_docs_result["metadatas"]) else {}
            documents.append(Document(page_content=doc_content, metadata=metadata))

        if documents:
            return BM25Retriever.from_documents(
                documents=documents,
                k=vector_config["k"],
            )
        return None

    async def _get_all_documents(self) -> list[Document]:
        all_docs = await self.vector_store.get(include=["documents", "metadatas"])
        documents = []
        for i, doc in enumerate(all_docs["documents"]):
            metadata = all_docs["metadatas"][i] if i < len(all_docs["metadatas"]) else {}
            documents.append(Document(page_content=doc, metadata=metadata))
        return documents

    async def get_retriever(self, query: str = None, user_id: str = None) -> BaseRetriever:
        if not user_id:
            return EmptyRetriever()

        filter_dict = {"user_id": user_id}
        vector_retriever = PgVectorRetriever(
            vector_store=self.vector_store,
            search_kwargs={"k": vector_config["k"], "filter": filter_dict},
        )
        bm25_retriever = await self.get_bm25_retriever(user_id)

        if bm25_retriever:
            weights = await self.get_dynamic_weights(query)
            return EnsembleRetriever(
                retrievers=[vector_retriever, bm25_retriever],
                weights=weights,
            )
        return vector_retriever

    @staticmethod
    async def get_dynamic_weights(query: str = None):
        default_vector_weight = 0.5
        default_bm25_weight = 0.5

        if not query:
            return [default_vector_weight, default_bm25_weight]

        query_length = len(query)
        query_words = len(query.split())

        if query_length > 50:
            vector_weight = 0.7
            bm25_weight = 0.3
        elif query_length < 20:
            vector_weight = 0.3
            bm25_weight = 0.7
        else:
            vector_weight = default_vector_weight
            bm25_weight = default_bm25_weight

        if query_words > 0:
            word_density = query_words / query_length
            if word_density > 0.1:
                bm25_weight = min(bm25_weight + 0.1, 0.7)
                vector_weight = max(vector_weight - 0.1, 0.3)

        return [vector_weight, bm25_weight]
