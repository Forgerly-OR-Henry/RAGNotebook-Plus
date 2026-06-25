# ModelScope 重排序模型配置

本项目使用 `BAAI/bge-reranker-v2-m3` 对 RAG 候选片段做重排序。模型由后端后台初始化流程检查和加载，路径通过当前运行 env 中的 `RERANKER_MODEL_PATH` 配置。

## 模型用途

重排序模型用于把向量检索和文本检索得到的候选片段重新排序，让最终进入 LLM 总结阶段的内容更贴近用户问题。它会影响知识库问答、笔记关联推荐等 RAG 链路的回答质量。

## 环境要求

| 环境 | 推荐 |
| --- | --- |
| Python | 3.12+ |
| PyTorch | 2.x |
| sentence-transformers | 随后端依赖安装 |
| 硬件 | CPU 可运行，NVIDIA GPU 更快 |

后端依赖已经在 `backend/pyproject.toml` 和 `backend/requirements.txt` 中声明，通常不需要单独安装。首次准备环境时运行：

```bash
cd backend
uv sync
```

如果没有安装 `uv`，可使用：

```bash
cd backend
python -m pip install -r requirements.txt
```

## 配置方式

统一启动时在 `config/.env` 中配置，后端单独启动时在 `backend/config/.env` 中配置：

```env
RERANKER_MODEL_PATH=D:\Hugging_Face\models\bge-reranker-v2-m3
```

路径不存在时，后端会尝试通过 ModelScope 下载模型。下载完成后，服务会在后台初始化重排序服务；后台初始化不应阻塞 FastAPI 进程启动。

## 手动下载

如需离线或提前准备模型：

1. 访问 [BAAI/bge-reranker-v2-m3](https://www.modelscope.cn/models/BAAI/bge-reranker-v2-m3)。
2. 下载完整模型目录到本地。
3. 将当前运行 env 的 `RERANKER_MODEL_PATH` 指向该目录。
4. 重启后端。

推荐目录示例：

```text
D:\Hugging_Face\models\bge-reranker-v2-m3
```

## 常见问题

### 启动时提示模型路径不存在

- 检查 `RERANKER_MODEL_PATH` 是否拼写正确。
- Windows 路径可直接使用反斜杠，例如 `D:\Hugging_Face\models\bge-reranker-v2-m3`。
- 如果依赖自动下载，确认当前环境可以访问 ModelScope。

### CUDA 内存不足

- 使用 CPU 运行重排序。
- 减少候选片段数量或批处理大小。
- 关闭其他占用显存的进程。

### 首次问答较慢

首次加载模型会有初始化成本。模型加载后，后续请求会复用同一个重排序服务。

## 验收

启动后端后，查看日志中是否出现重排序模型初始化成功的信息。也可以通过一次知识库问答或笔记关联推荐验证 RAG 链路是否正常返回。

---

[返回首页](../README.md)
