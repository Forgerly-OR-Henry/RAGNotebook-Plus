"""
模块职责：RAG 检索增强服务，负责问题改写、召回、重排和上下文拼装。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
from collections.abc import Awaitable, Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from core.background_init import init_manager
from core.logger_handler import logger
from agent.prompts.loader import load_prompt

SourceSearch = Callable[[str, str, str, int], Awaitable[list]]


class RagService:
    """
    用途：业务服务类，用于封装用例流程、依赖协作和事务边界。

    属性：
    - retriever（实例属性，由构造函数注入或初始化）：保存retriever相关状态、配置或数据字段。
    - user_id（实例属性，由构造函数注入或初始化）：保存user_id相关状态、配置或数据字段。
    - source_search（实例属性，由构造函数注入或初始化）：保存source_search相关状态、配置或数据字段。
    - prompt_text（实例属性，由构造函数注入或初始化）：保存prompt_text相关状态、配置或数据字段。
    - prompt_template（实例属性，由构造函数注入或初始化）：保存prompt_template相关状态、配置或数据字段。
    - chat_model（实例属性，由构造函数注入或初始化）：保存chat_model相关状态、配置或数据字段。
    - chain（实例属性，由构造函数注入或初始化）：保存chain相关状态、配置或数据字段。
    - hyde_prompt_template（实例属性，由构造函数注入或初始化）：保存hyde_prompt_template相关状态、配置或数据字段。
    - thinking_callback（实例属性，由构造函数注入或初始化）：保存thinking_callback相关状态、配置或数据字段。
    """
    def __init__(self, user_id: str = None, thinking_callback=None, source_search: SourceSearch | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - user_id（str）：调用方传入的user_id数据或控制参数，用于驱动本函数处理流程。
        - thinking_callback（未显式标注）：调用方传入的thinking_callback数据或控制参数，用于驱动本函数处理流程。
        - source_search（SourceSearch | None）：调用方传入的source_search数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self.retriever = None
        self.user_id = user_id
        self.source_search = source_search
        self.prompt_text = load_prompt(prompt_type="rag_summary_prompt")
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.chat_model = init_manager.chat_model
        self.chain = self._init_chain() if self.chat_model is not None else None
        self.hyde_prompt_template = PromptTemplate.from_template(
            "基于以下问题，生成一个详细的假设性回答，我会根据你的这个假设性回答"
            "在向量数据库里检索文档：\n\n问题：{query}\n\n假设性回答："
        )
        self.thinking_callback = thinking_callback

    async def initialize_retriever(self, query: str = None):
        """
        初始化检索器
        :param query: 查询语句，用于动态调整权重
        """
        if self.thinking_callback:
            await self.thinking_callback({
                "type": "thinking",
                "stage": "retrieval",
                "content": "初始化统一来源检索器",
            })


    def _init_chain(self):
        """初始化链"""
        chain = (
                self.prompt_template
                | self.chat_model
                | StrOutputParser()
        )
        return chain

    async def generate_hypothetical_document(self, query: str) -> str:
        """
        使用HyDE技术生成假设性文档
        :param query: 用户查询
        :return: 假设性文档内容
        """
        if self.chat_model is None:
            logger.warning("【HyDE】chat_model未初始化，使用原始查询进行检索")
            return query

        try:
            hyde_chain = (
                self.hyde_prompt_template
                | self.chat_model
                | StrOutputParser()
            )
            hypothetical_doc = await hyde_chain.ainvoke({"query": query})
            logger.info(f"【HyDE】生成的假设性文档:\n{hypothetical_doc}")
            return hypothetical_doc
        except Exception as e:
            logger.error(f"【HyDE】生成假设性文档失败: {e}")
            return query

    async def retrieve_document(self, query: str, use_hyde: bool = True) -> list:
        """使用HyDE技术 从向量数据库里检索文档"""
        if not self.user_id:
            logger.warning("【HyDE】user_id为空，不进行任何检索")
            return []

        try:
            await self.initialize_retriever(query)

            retrieval_query = query
            if use_hyde:
                # 使用HyDE技术生成假设性文档
                logger.info(f"【HyDE】开始处理查询: {query}")

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "hyde",
                        "content": f"正在基于查询「{query}」生成假设性文档..."
                    })

                retrieval_query = await self.generate_hypothetical_document(query)

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "hyde",
                        "content": "假设性文档生成完成",
                        "details": {
                            "hypothetical_doc_preview": retrieval_query[:200] + "..." if len(retrieval_query) > 200 else retrieval_query
                        }
                    })

                logger.info("【HyDE】使用假设性文档进行统一来源检索")
            else:
                logger.info(f"【RAG】使用原始查询进行快速检索: {query}")

            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "retrieval",
                    "content": "正在向量数据库中检索相关文档..."
                })

            if self.source_search is None:
                logger.warning("【HyDE】source_search未注入，不进行任何检索")
                return []

            chunks = await self.source_search(self.user_id, retrieval_query, "mixed", 6)

            logger.info(f"【HyDE】检索到 {len(chunks)} 个来源片段")

            if self.thinking_callback:
                doc_previews = []
                for i, chunk in enumerate(chunks, 1):
                    preview = chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content
                    source = f"{'笔记' if chunk.source_type == 'note' else '知识库'}《{chunk.title}》"
                    doc_previews.append({
                        "index": i,
                        "preview": preview,
                        "source": source,
                    })
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "retrieval",
                    "content": f"检索到 {len(chunks)} 个相关来源片段",
                    "details": {
                        "documents": doc_previews
                    }
                })

            return chunks
        except Exception as e:
            logger.error(f"【HyDE】检索文档失败: {e}")
            return []

    async def reorder_documents(self, query: str, documents: list) -> list:
        """
        对文档进行重排序
        :param query: 查询语句
        :param documents: 文档列表
        :return: 重排序后的文档列表
        """
        if self.thinking_callback:
            await self.thinking_callback({
                "type": "thinking",
                "stage": "reorder",
                "content": f"正在对 {len(documents)} 个文档进行重排序..."
            })

        reorder_backend = init_manager.reorder_service
        if reorder_backend is None:
            from agent.rag.reorder_service import reorder_service as fallback_reorder_service
            reorder_backend = fallback_reorder_service

        result = await reorder_backend.reorder_documents(query, documents, thinking_callback=self.thinking_callback)
        if result["success"]:
            # 提取重排序后的文档内容
            reordered_documents = [doc.get("document", "") for doc in result["documents"]]
            logger.info(f"【RAG】文档重排序成功，返回 {len(reordered_documents)} 个文档")

            if self.thinking_callback:
                score_details = []
                for i, doc in enumerate(result["documents"], 1):
                    score_details.append({
                        "rank": i,
                        "score": round(doc.get("similarity", 0), 4),
                        "preview": doc.get("document", "")[:100] + "..." if len(doc.get("document", "")) > 100 else doc.get("document", "")
                    })
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "reorder",
                    "content": f"重排序完成，返回 {len(reordered_documents)} 个文档",
                    "details": {
                        "scores": score_details
                    }
                })

            return reordered_documents
        else:
            logger.warning(f"【RAG】重排序失败: {result['error']}")
            return documents

    async def get_documents_and_summary(self, query: str) -> dict:
        """
        获取文档列表和摘要
        :param query: 查询语句
        :return: 包含文档列表和摘要的字典
        """
        if not self.user_id:
            logger.warning("【RAG】user_id为空，不返回任何文档")
            return {
                "documents": [],
                "summary": "抱歉，我没有找到相关的信息。"
            }

        try:
            documents = await self.retrieve_document(query)

            # 提取文档内容列表，附上来源标记供 LLM 引用
            def _format_doc(chunk):
                """
                用途：格式化format doc相关的数据或流程。

                参数：
                - chunk（未显式标注）：调用方传入的chunk数据或控制参数，用于驱动本函数处理流程。

                返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
                """
                source_label = "笔记" if chunk.source_type == "note" else "知识库"
                return f"[来源：{source_label}《{chunk.title}》]\n{chunk.content}"

            document_contents = [_format_doc(doc) for doc in documents]

            # 对文档进行重排序
            reordered_documents = await self.reorder_documents(query, document_contents)

            # 如果没有检索到文档
            if not reordered_documents:
                return {
                    "documents": [],
                    "summary": "抱歉，我没有找到相关的信息。"
                }

            # 使用分批总结策略
            try:
                if self.chain is None:
                    logger.error("【RAG】chat_model未初始化，无法生成摘要")
                    return {
                        "documents": reordered_documents,
                        "summary": "抱歉，AI 模型仍在初始化，请稍后再试。"
                    }

                # 对每个文档单独总结（使用线程池并发处理）
                individual_summaries = []
                max_documents = 3  # 使用前3个最相关的文档

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "summarize",
                        "content": f"正在对前 {min(max_documents, len(reordered_documents))} 个最相关文档进行总结..."
                    })

                # 定义单个文档总结函数
                async def summarize_document(i, doc):
                    """
                    用途：异步执行summarize document相关业务流程。

                    参数：
                    - i（未显式标注）：调用方传入的i数据或控制参数，用于驱动本函数处理流程。
                    - doc（未显式标注）：调用方传入的doc数据或控制参数，用于驱动本函数处理流程。

                    返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

                    副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
                    """
                    logger.info(f"【RAG】正在总结第{i}个文档")
                    if self.thinking_callback:
                        await self.thinking_callback({
                            "type": "thinking",
                            "stage": "summarize",
                            "content": f"正在总结第 {i} 个文档..."
                        })
                    # 为单个文档构建上下文
                    single_context = f"【参考资料{i}】:{doc}\n"
                    # 生成单个文档的摘要
                    import time
                    start_time = time.time()
                    single_summary = await asyncio.wait_for(
                        self.chain.ainvoke({"input": query, "context": single_context}),
                        timeout=30.0  # 单个文档总结超时时间
                    )
                    end_time = time.time()
                    logger.info(f"【RAG】第{i}个文档总结耗时: {end_time - start_time:.2f}秒")
                    return single_summary

                # 使用线程池并发处理文档总结
                tasks = []
                for i, doc in enumerate(reordered_documents[:max_documents], 1):
                    tasks.append(summarize_document(i, doc))

                # 并发执行所有总结任务，最多5个线程
                import time
                start_time = time.time()
                individual_summaries = await asyncio.gather(*tasks)
                end_time = time.time()
                logger.info(f"【RAG】所有文档总结完成，总耗时: {end_time - start_time:.2f}秒")

                # 如果只有一个文档，直接返回其摘要
                if len(individual_summaries) == 1:
                    logger.info("【RAG】生成摘要成功")
                    return {
                        "documents": reordered_documents,
                        "summary": individual_summaries[0]
                    }

                # 合并多个文档的摘要，生成最终总结
                combined_context = "以下是多个文档的摘要，请综合这些信息生成最终的回答：\n\n"
                for i, summary in enumerate(individual_summaries, 1):
                    combined_context += f"【文档{i}摘要】:{summary}\n\n"

                logger.info("【RAG】合并摘要完成，开始生成最终总结")

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "summarize",
                        "content": "正在综合多个文档生成最终回答..."
                    })

                # 生成最终总结
                final_summary = await asyncio.wait_for(
                    self.chain.ainvoke({"input": query, "context": combined_context}),
                    timeout=30.0  # 最终总结超时时间
                )

                logger.info("【RAG】生成摘要成功")
                return {
                    "documents": reordered_documents,
                    "summary": final_summary
                }
            except TimeoutError:
                logger.error("【RAG】生成摘要超时")
                return {
                    "documents": reordered_documents,
                    "summary": "抱歉，生成摘要超时，请稍后再试。"
                }
        except Exception as e:
            logger.error(f"【RAG】生成摘要失败: {e}", exc_info=True)
            return {
                "documents": [],
                "summary": "抱歉，处理您的请求时出现了错误。"
            }

    async def get_reordered_documents(self, query: str, max_documents: int = 3, use_hyde: bool = False) -> list[str]:
        """Return formatted, reranked documents for the fast streaming chat path."""
        documents = await self.retrieve_document(query, use_hyde=use_hyde)

        def _format_doc(chunk):
            """
            用途：格式化format doc相关的数据或流程。

            参数：
            - chunk（未显式标注）：调用方传入的chunk数据或控制参数，用于驱动本函数处理流程。

            返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
            """
            source_label = "笔记" if chunk.source_type == "note" else "知识库"
            return f"[来源：{source_label}《{chunk.title}》]\n{chunk.content}"

        document_contents = [_format_doc(doc) for doc in documents]
        reordered_documents = await self.reorder_documents(query, document_contents)
        return reordered_documents[:max_documents]

    async def rag_summary(self, query: str) -> str:
        """RAG 摘要"""
        result = await self.get_documents_and_summary(query)
        return result.get("summary", "抱歉，处理您的请求时出现了错误。")

if __name__ == '__main__':
    import asyncio

    async def main():
        """
        用途：作为命令行或模块入口执行main相关的数据或流程。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。

        副作用：可能访问数据库、文件、模型服务或流式事件通道，异常会沿调用链抛出。
        """
        service = RagService()
        await service.initialize_retriever()
        result = await service.rag_summary("小户型适合什么扫地机器人")
        print(result)

    asyncio.run(main())
