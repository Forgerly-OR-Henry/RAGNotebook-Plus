"""
模块职责：项目源码模块，封装 RAGNotebook 的可维护业务逻辑。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

import asyncio
import time

from core.logger_handler import logger


class _BackgroundInitManager:
    """后台初始化管理器

    在 FastAPI 启动后通过 start() 在后台异步初始化所有重型资源，
    避免模块级导入阻塞 uvicorn 启动。
    每个组件初始化完成后设置对应的 Event。
    """

    def __init__(self):
        """
        用途：执行init相关业务逻辑。

        参数：无显式业务参数。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        self._started = False
        self._finished = False
        self._failed = False
        self._error: str | None = None
        self._current_step = "pending"
        self._start_time = 0.0

        # 各组件的初始化状态事件
        self.models_ready = asyncio.Event()
        self.note_service_ready = asyncio.Event()
        self.reranker_ready = asyncio.Event()

        # 初始化后的实例（初始化完成前为 None）
        self.chat_model = None
        self.embed_model = None
        self.vision_model = None
        self.note_service = None
        self.reorder_service = None

    async def start(self):
        """启动后台初始化（不阻塞主事件循环）"""
        if self._started:
            return
        self._started = True
        self._current_step = "starting"
        self._start_time = time.time()
        asyncio.create_task(self._initialize_all())

    def status_snapshot(self) -> dict:
        """Return a lightweight readiness snapshot for health checks and the frontend."""
        if self._failed:
            status = "failed"
        elif self._finished:
            status = "ready"
        elif self._started:
            status = "starting"
        else:
            status = "pending"

        elapsed = time.time() - self._start_time if self._start_time else 0.0
        return {
            "status": status,
            "started": self._started,
            "elapsed_seconds": round(elapsed, 1),
            "current_step": self._current_step,
            "error": self._error,
            "components": {
                "models": self.models_ready.is_set(),
                "note_service": self.note_service_ready.is_set(),
                "reranker": self.reranker_ready.is_set(),
            },
        }

    async def _initialize_all(self):
        """后台执行所有重型初始化"""
        try:
            logger.info("🔄 开始后台初始化...")

            # 1. AI 模型（调用 factory 中的工厂类）
            await self._init_models()

            # 2. pgvector-backed NoteService（依赖 embed_model）
            await self._init_note_service()

            # 3. 重排序模型（引入 torch、sentence_transformers 等重型框架）
            await self._init_reranker()

            elapsed = time.time() - self._start_time
            self._finished = True
            self._current_step = "ready"
            logger.info(f"✅ 后台初始化完成，耗时 {elapsed:.1f} 秒")

        except Exception as e:
            self._failed = True
            self._error = str(e)
            self._current_step = "failed"
            logger.error(f"❌ 后台初始化失败: {e}", exc_info=True)

    async def _init_models(self):
        """初始化 AI 模型"""
        from agent.models.factory import ChatModelFactory, EmbedModelFactory, VisionModelFactory

        self._current_step = "loading_chat_model"
        self.chat_model = await asyncio.to_thread(
            lambda: ChatModelFactory().generator()
        )
        logger.info("✅ chat_model 初始化完成")

        self._current_step = "loading_embed_model"
        self.embed_model = await asyncio.to_thread(
            lambda: EmbedModelFactory().generator()
        )
        logger.info("✅ embed_model 初始化完成")
        await self._validate_embedding_dimension()

        self._current_step = "loading_vision_model"
        self.vision_model = await asyncio.to_thread(
            lambda: VisionModelFactory().generator()
        )
        logger.info("✅ vision_model 初始化完成")

        self.models_ready.set()

    async def _validate_embedding_dimension(self):
        """Fail early when the configured pgvector dimension does not match the embedding model."""
        from agent.indexing.index_repository import embedding_dimension

        expected_dim = embedding_dimension()
        sample_embedding = await asyncio.to_thread(self.embed_model.embed_query, "RAGNotebook embedding dimension check")
        actual_dim = len(sample_embedding or [])
        if actual_dim != expected_dim:
            raise RuntimeError(
                f"EMBEDDING_DIM={expected_dim} 与当前嵌入模型实际维度 {actual_dim} 不一致，"
                "请调整当前运行环境配置后重建空库。"
            )
        logger.info(f"✅ embedding 维度校验通过: {actual_dim}")

    async def _init_note_service(self):
        """初始化 NoteService（pgvector，依赖 embed_model）"""
        await self.models_ready.wait()

        from mvc.services.note_service import NoteService

        self._current_step = "loading_note_service"
        self.note_service = await asyncio.to_thread(
            lambda: NoteService(embed_model=self.embed_model)
        )
        logger.info("✅ NoteService（pgvector）初始化完成")
        self.note_service_ready.set()

    async def _init_reranker(self):
        """检查并初始化重排序模型（触发 torch 等重型框架加载）"""
        from agent.rag.reorder_service import ReorderService, check_and_download_reranker_model

        self._current_step = "checking_reranker_model"
        await asyncio.to_thread(check_and_download_reranker_model)
        logger.info("✅ 重排序模型检查完成")

        self._current_step = "loading_reranker_service"
        self.reorder_service = ReorderService()
        await self.reorder_service.warmup()
        logger.info("✅ ReorderService 初始化完成")
        self.reranker_ready.set()


# 全局单例
init_manager = _BackgroundInitManager()
