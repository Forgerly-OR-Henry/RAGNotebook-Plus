"""
模块职责：模型工厂模块，负责根据环境配置创建聊天模型、嵌入模型和重排模型。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from abc import ABC, abstractmethod
from http import HTTPStatus

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

from core.logger_handler import logger
from utils.env_loader import (
    load_backend_env,
    require_env_declared,
    require_env_int_value,
    require_env_value,
)

# 加载环境变量
load_backend_env()


class DashScopeEmbeddingsWrapper(Embeddings):
    """阿里云DashScope嵌入模型封装"""

    _DIMENSIONAL_MODELS = {"text-embedding-v3", "text-embedding-v4"}

    def __init__(self, model_name: str = "text-embedding-v4", api_key: str = None, embedding_dim: int | None = None):
        """
        用途：执行init相关业务逻辑。

        参数：
        - model_name（str）：调用方传入的model_name数据或控制参数，用于驱动本函数处理流程。
        - api_key（str）：调用方传入的api_key数据或控制参数，用于驱动本函数处理流程。
        - embedding_dim（int | None）：调用方传入的embedding_dim数据或控制参数，用于驱动本函数处理流程。

        返回：未显式标注；返回值供调用方继续编排业务流程或生成接口响应。
        """
        try:
            import dashscope
            self.dashscope = dashscope
            self.dashscope.api_key = (
                api_key
                or require_env_declared("ALIYUN_ACCESS_KEY_SECRET")
                or require_env_declared("DASHSCOPE_API_KEY")
                or None
            )
            self.model_name = model_name
            self.embedding_dim = embedding_dim if embedding_dim is not None else require_env_int_value("EMBEDDING_DIM", 1024)
        except ImportError:
            raise ImportError("需要安装 dashscope 库: pip install dashscope")

    def _call_embedding(self, inputs: str | list[str]) -> list[list[float]]:
        """
        用途：执行call embedding相关业务逻辑。

        参数：
        - inputs（str | list[str]）：调用方传入的inputs数据或控制参数，用于驱动本函数处理流程。

        返回：list[list[float]]；返回值供调用方继续编排业务流程或生成接口响应。
        """
        kwargs = {
            "model": self.model_name,
            "input": inputs,
        }
        if self.model_name in self._DIMENSIONAL_MODELS:
            kwargs["dimension"] = self.embedding_dim

        resp = self.dashscope.TextEmbedding.call(**kwargs)
        if getattr(resp, "status_code", None) != HTTPStatus.OK:
            message = getattr(resp, "message", "") or getattr(resp, "code", "") or str(resp)
            logger.error(f"阿里云嵌入调用失败: {message}")
            raise RuntimeError(f"嵌入调用失败: {message}")

        output = getattr(resp, "output", None) or {}
        embeddings = output.get("embeddings", []) if isinstance(output, dict) else output["embeddings"]
        if not embeddings:
            raise RuntimeError("嵌入调用失败: DashScope 响应中缺少 embeddings")
        return [emb["embedding"] for emb in embeddings]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档 — 按 batch_size 分组合并 API 调用"""
        if not texts:
            return []
        batch_size = 10
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self._call_embedding(batch if len(batch) > 1 else batch[0]))
        return results

    def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询"""
        return self._call_embedding(text)[0]


class BaseModelFactory(ABC):
    """基础模型工厂"""

    @abstractmethod
    def generator(self) -> Embeddings | BaseChatModel | None:
        """生成模型"""
        pass


class ChatModelFactory(BaseModelFactory):
    """聊天模型工厂 - 支持阿里云百炼和Ollama"""

    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据LLM_TYPE生成对应的聊天模型"""
        llm_type = require_env_value("LLM_TYPE", "ALIYUN").upper()

        if llm_type == "OLLAMA":
            model_name = (
                require_env_declared("OLLAMA_MODEL_NAME")
                or require_env_declared("OLLAMA_CHAT_MODEL_NAME")
                or "qwen3:7b"
            )
            base_url = require_env_value("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"📦 ChatModel 使用Ollama模型: {model_name}, 地址: {base_url}")

            return ChatOllama(
                model=model_name,
                base_url=base_url,
                streaming=True,
                top_p=0.7,
            )

        elif llm_type == "ALIYUN":
            model_name = require_env_declared("ALIYUN_MODEL_NAME") or require_env_value("CHAT_MODEL_NAME", "qwen3-max")
            api_key = require_env_value("ALIYUN_ACCESS_KEY_SECRET")
            base_url = require_env_value("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

            logger.info(f"📦 ChatModel 使用阿里云百炼模型: {model_name}")

            return ChatTongyi(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                streaming=True,
                top_p=0.7,
            )

        else:
            raise ValueError(f"不支持的LLM_TYPE: {llm_type}，可选值: ALIYUN, OLLAMA")


class EmbedModelFactory(BaseModelFactory):
    """嵌入模型工厂 - 支持Ollama和阿里云百炼"""
    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据EMBED_MODEL_TYPE生成对应的嵌入模型"""
        embed_type = require_env_value("EMBED_MODEL_TYPE", "OLLAMA").upper()

        if embed_type == "OLLAMA":
            model_name = require_env_value("TEXT_EMBEDDING_MODEL_NAME", "qwen3-embedding:0.6b")
            base_url = require_env_value("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"📦 EmbedModel 使用Ollama嵌入模型: {model_name}, 地址: {base_url}")

            return OllamaEmbeddings(
                model=model_name,
                base_url=base_url
            )

        elif embed_type == "ALIYUN":
            model_name = require_env_value("ALIYUN_EMBED_MODEL_NAME", "text-embedding-v4")
            api_key = require_env_value("ALIYUN_ACCESS_KEY_SECRET")
            embedding_dim = require_env_int_value("EMBEDDING_DIM", 1024)

            logger.info(f"📦 EmbedModel 使用阿里云嵌入模型: {model_name}, 维度: {embedding_dim}")

            return DashScopeEmbeddingsWrapper(
                model_name=model_name,
                api_key=api_key,
                embedding_dim=embedding_dim
            )

        else:
            raise ValueError(f"不支持的EMBED_MODEL_TYPE: {embed_type}，可选值: OLLAMA, ALIYUN")


class VisionModelFactory(BaseModelFactory):
    """
    视觉模型工厂 - 支持阿里云百炼和Ollama多模态模型。
    用于 PDF 多模态加载场景：将 PDF 页面渲染为图片，然后调用视觉模型进行图片理解，
    提取纯文本提取难以获取的图表、表格、流程图等视觉信息。

    之所以单独为一个视觉模型工厂而不是复用 ChatModelFactory，是因为：
    1. ChatModel 使用 streaming=True（流式输出），而视觉模型只能用 streaming=False
       （图片理解不适合流式）
    2. 视觉模型可能有独立的模型配置（如 VISION_OLLAMA_MODEL_NAME 区分于 OLLAMA_MODEL_NAME）
    3. 部分用户可能希望视觉模型使用更大的参数量或专门的多模态模型（如 qwen-vl 系列）
    """

    def generator(self) -> BaseChatModel | None:
        """根据VISION_MODEL_TYPE生成对应的视觉模型"""
        vision_type = require_env_declared("VISION_MODEL_TYPE").strip().upper()
        if not vision_type:
            raise ValueError("VISION_MODEL_TYPE 必须显式配置，可选值: ALIYUN, OLLAMA")

        if vision_type == "OLLAMA":
            model_name = require_env_declared("VISION_OLLAMA_MODEL_NAME") or require_env_declared("OLLAMA_MODEL_NAME") or "qwen-vl:7b"
            base_url = require_env_value("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"🎨 VisionModel 使用Ollama多模态模型: {model_name}, 地址: {base_url}")

            return ChatOllama(
                model=model_name,
                base_url=base_url,
                # 视觉模型禁用 streaming，因为图片理解需要在完整的上下文上做推理
                streaming=False,
                top_p=0.7,
            )

        elif vision_type == "ALIYUN":
            model_name = require_env_declared("VISION_CHAT_MODEL_NAME") or require_env_value("CHAT_MODEL_NAME", "qwen3-max")
            api_key = require_env_value("ALIYUN_ACCESS_KEY_SECRET")
            base_url = require_env_value("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

            logger.info(f"🎨 VisionModel 使用阿里云百炼多模态模型: {model_name}")

            return ChatTongyi(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                streaming=False,
                top_p=0.7,
            )

        else:
            raise ValueError(f"不支持的VISION_MODEL_TYPE: {vision_type}，可选值: ALIYUN, OLLAMA")


class RerankerModelFactory(BaseModelFactory):
    """重排序模型工厂 - 已废弃，使用CrossEncoder模型"""
    def generator(self) -> Embeddings | BaseChatModel | None:
        """生成模型"""
        return None


chat_model = None
embed_model = None
reranker_model = None
vision_model = None
