import os
from pathlib import Path
from typing import Any

from core.logger_handler import logger
from utils.env_loader import load_backend_env

# 加载环境变量
load_backend_env()

DEFAULT_RERANKER_MODEL_PATH = r"models\bge-reranker-v2-m3"


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def resolve_reranker_model_path(path_value: str | None = None) -> Path:
    configured_path = path_value or os.getenv("RERANKER_MODEL_PATH", DEFAULT_RERANKER_MODEL_PATH)
    model_path = Path(configured_path.strip().strip('"').strip("'"))
    if model_path.is_absolute():
        return model_path
    return (project_root() / model_path).resolve()


def find_model_path(base_path: str) -> str:
    base = Path(base_path)
    if (base / 'config.json').exists():
        return str(base)

    for root, dirs, files in os.walk(base):
        if 'config.json' in files:
            return str(root)

    logger.info(f"✅ 模型路径：{base}")
    return str(base)


def has_model_config(base_path: Path) -> bool:
    actual_model_path = Path(find_model_path(str(base_path)))
    return (actual_model_path / 'config.json').exists()


def check_and_download_reranker_model() -> None:
    """检查并重排序模型，在FastAPI启动时执行"""
    from modelscope import snapshot_download
    from tqdm import tqdm

    LOCAL_MODEL_PATH = resolve_reranker_model_path()
    MODELSCOPE_MODEL_NAME = "BAAI/bge-reranker-v2-m3"

    try:
        if LOCAL_MODEL_PATH.exists() and LOCAL_MODEL_PATH.is_dir() and has_model_config(LOCAL_MODEL_PATH):
            logger.info(f"✅ 检测到本地重排序模型：{LOCAL_MODEL_PATH}")
        else:
            logger.warning(f"⚠️  本地模型未找到：{LOCAL_MODEL_PATH}")
            logger.info(f"🔄 开始从魔搭社区下载模型：{MODELSCOPE_MODEL_NAME}")

            LOCAL_MODEL_PATH.mkdir(parents=True, exist_ok=True)

            with tqdm(total=100, desc='下载模型', leave=True, bar_format='{l_bar}{bar}| {n_fmt}%') as pbar:
                pbar.update(10)
                snapshot_download(
                    model_id=MODELSCOPE_MODEL_NAME,
                    cache_dir=str(LOCAL_MODEL_PATH),
                    revision='master'
                )
                pbar.update(90)

            logger.info(f"✅ 模型下载完成，保存路径：{LOCAL_MODEL_PATH}")

    except Exception as e:
        logger.error(f"❌ 模型检查失败: {str(e)}")
        raise RuntimeError(f"重排序模型检查失败: {str(e)}")


class ReorderService:
    """文档重排序服务"""

    def __init__(self):
        import torch

        self.LOCAL_MODEL_PATH = str(resolve_reranker_model_path())
        self.MODELSCOPE_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None

    async def _get_model(self):
        """懒加载模型实例"""
        from sentence_transformers import CrossEncoder

        if self._model is None:
            actual_model_path = find_model_path(self.LOCAL_MODEL_PATH)
            logger.info(f"✅ 加载重排序模型：{actual_model_path}")
            self._model = CrossEncoder(
                actual_model_path,
                max_length=512,
                device=self.device,
                local_files_only=True
            )
            self._model.eval()
            logger.info(f"✅ 模型加载成功，使用设备：{self.device}")
        return self._model

    async def warmup(self) -> None:
        """Load the reranker model during background startup."""
        await self._get_model()

    @property
    async def model(self):
        """获取模型实例（懒加载）"""
        return await self._get_model()

    async def reorder_documents(self, query: str, documents: list[str], thinking_callback=None) -> dict[str, Any]:
        """
        对文档进行重排序
        :param query: 查询语句
        :param documents: 文档列表
        :param thinking_callback: 思考过程回调函数
        :return: 包含重排序结果的字典，格式为：
                 {"success": bool, "documents": List[Dict], "error": str}
        """
        try:
            if not documents:
                return {
                    "success": True,
                    "documents": [],
                    "error": ""
                }

            if thinking_callback:
                await thinking_callback({
                    "type": "thinking",
                    "stage": "reorder",
                    "content": f"正在计算 {len(documents)} 个文档的相关性分数..."
                })

            # 构造查询+文档对
            pairs = [(query, doc) for doc in documents]

            # 使用模型进行批量预测（batch_size=1避免padding令牌报错）
            model = await self.model
            # 禁用梯度计算，提高推理性能
            import torch
            with torch.no_grad():
                scores = model.predict(pairs, batch_size=1)

            # 构建结果列表
            scored_documents = []
            for doc, score in zip(documents, scores):
                scored_documents.append({
                    "document": doc,
                    "similarity": float(score)
                })
                logger.info(f"【重排序服务】文档相似度分数: {score:.4f}")

            if thinking_callback:
                score_details = []
                for i, (doc, score) in enumerate(zip(documents, scores), 1):
                    score_details.append({
                        "index": i,
                        "score": round(float(score), 4),
                        "preview": doc[:100] + "..." if len(doc) > 100 else doc
                    })
                await thinking_callback({
                    "type": "thinking",
                    "stage": "reorder",
                    "content": f"已计算完成 {len(documents)} 个文档的相关性分数，按分数降序排序",
                    "details": {
                        "scores": score_details
                    }
                })

            # 按相似度分数降序排序
            sorted_docs = sorted(scored_documents, key=lambda x: x["similarity"], reverse=True)
            logger.info(f"【重排序服务】文档重排序成功，返回 {len(sorted_docs)} 个文档")

            return {
                "success": True,
                "documents": sorted_docs,
                "error": ""
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"【重排序服务】重排序失败: {error_msg}")
            return {
                "success": False,
                "documents": [],
                "error": error_msg
            }

    @staticmethod
    async def format_reorder_result(sorted_docs: list[dict]) -> str:
        """
        格式化重排序结果
        :param sorted_docs: 重排序后的文档列表
        :return: 格式化后的字符串
        """
        formatted_result = "重排序后的文档列表：\n"
        for i, doc in enumerate(sorted_docs, 1):
            formatted_result += f"{i}. 相似度: {doc.get('similarity', 0):.4f}\n"
            formatted_result += f"   内容: {doc.get('document', '')}\n\n"
        return formatted_result


# 全局重排序服务实例
reorder_service = ReorderService()
