# 故障排除

本文按本地启动链路整理常见问题。统一启动优先确认 `config/.env`；后端单独启动确认 `backend/.env`；前端单独启动确认 `front/.env`。

## 1. API Key 错误

现象：

- 模型调用返回 `Invalid API Key`、`API Key expired` 或鉴权失败。
- 后台初始化聊天模型、嵌入模型或视觉模型失败。

处理：

- 统一启动时，确认 `config/.env` 中 `ALIYUN_ACCESS_KEY_SECRET=apikey.txt`，且 `config/apikey.txt` 存在。
- 后端单独启动时，确认 `backend/.env` 中 `ALIYUN_ACCESS_KEY_SECRET=../config/apikey.txt` 或其他有效 key 文件路径。
- key 文件只放一行真实 key，不写变量名。
- 确认 key 未过期，且有对应模型服务权限。
- 如果使用本地模型，将 `LLM_TYPE`、`EMBED_MODEL_TYPE` 或 `VISION_MODEL_TYPE` 切换为 `OLLAMA`，并确认 Ollama 服务可访问。

## 2. PostgreSQL 连接失败

现象：

- `connection refused`
- `password authentication failed`
- `database does not exist`
- `PostgreSQL is not reachable`

处理：

- 运行 `docker compose up -d postgres`。
- 统一启动时检查 `config/.env`；后端单独启动时检查 `backend/.env`。确认 `DATABASE_URL` 与 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_HOST`、`POSTGRES_PORT`、`POSTGRES_DB` 一致。
- `DATABASE_URL` 优先级最高；如果它和 `POSTGRES_*` 冲突，`start.py` 会直接报错。
- 如果修改过数据库用户名或密码，但 Docker 卷已经初始化，需要同步修改数据库内用户，或清理本地数据库卷后重新初始化。
- 确认端口 `5432` 未被其他服务占用。

## 3. pgvector 初始化失败

现象：

- `extension "vector" is not available`
- `CREATE EXTENSION vector` 失败
- `type vector does not exist`

处理：

- 本地优先使用仓库默认的 `docker-compose.yml`，镜像为 `pgvector/pgvector:pg16`。
- 如果使用外部 PostgreSQL，确认服务端已安装 pgvector 扩展。
- 用有权限的数据库用户执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- 如果当前库来自旧版本或已经创建过不兼容表，清空 `public` schema 或重建 `POSTGRES_DB` 后重新启动后端。
- 后端启动会自动执行 `CREATE EXTENSION IF NOT EXISTS vector` 并创建 `index_chunks`。

## 4. 向量维度不匹配

现象：

- 插入向量时报维度不一致。
- 更换嵌入模型后检索或上传失败。

处理：

- 确认当前运行 env 的 `EMBEDDING_DIM` 等于当前嵌入模型实际输出维度。
- 阿里云百炼文本向量请使用有效模型名，例如 `text-embedding-v4`；`qwen3-embedding` 不是 DashScope 同步文本向量接口的模型名，会返回 `Model not exist`。
- 切换嵌入模型后，已有 `index_chunks.embedding` 列维度不会自动改变，需要重建本地测试库。
- 云端和本地嵌入模型不要混用同一批历史向量，除非输出维度和语义空间兼容。

## 5. OpenAPI 导入失败

现象：

- `ModuleNotFoundError: No module named 'main'`
- `ModuleNotFoundError: No module named 'controllers'`
- 生成 OpenAPI 时路径数量明显不完整。

处理：

- 后端命令都应在 `backend` 目录执行，并设置 `PYTHONPATH=src`。

```powershell
cd backend
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -c "from main import app; print(len(app.openapi().get('paths', {})))"
```

- 如果没有 `.venv`，先安装依赖：

```bash
cd backend
uv sync
```

或：

```bash
cd backend
python -m pip install -r requirements.txt
```

## 6. 后端依赖或 python-magic 失败

现象：

- `python-magic native library is unavailable`
- 上传文件 MIME 检测失败。
- `ModuleNotFoundError`。

处理：

- 运行 `python start.py --install`。
- Windows 环境确认已安装 `python-magic-bin`。
- 使用 `backend/.venv` 中的解释器启动后端，避免系统 Python 缺依赖。
- 如果手动启动，确认命令类似：

```powershell
cd backend
.venv\Scripts\python.exe src\main.py
```

## 7. 文件上传失败

现象：

- `File too large`
- `Unsupported file type`
- 上传后没有切片或切片为空。

处理：

- 当前知识库支持 TXT / PDF / MD / PPTX / DOCX。
- 文件类型白名单在 `backend/src/mvc/services/knowledge_service.py`。
- 检查文件大小是否超过后端限制。
- PDF 图片解析依赖视觉模型，视觉模型不可用时复杂版式解析质量会下降。
- 上传失败后可查看后端日志和 `/knowledge/documents` 返回的 SSE `error` 事件。

## 8. 重排序模型加载失败

现象：

- `RuntimeError: 重排序模型加载失败`
- 指定模型目录不存在。
- 首次启动卡在模型下载。

处理：

- 检查当前运行 env 中 `RERANKER_MODEL_PATH` 是否存在。
- 可手动下载 `BAAI/bge-reranker-v2-m3`，详见 [modelscope_model.md](./modelscope_model.md)。
- 无网络环境下不要依赖自动下载。
- 显存不足时使用 CPU 或减少候选片段数量。

## 9. Ollama 连接失败

现象：

- `Connection refused`
- 本地模型调用超时。

处理：

- 启动 Ollama：

```bash
ollama serve
```

- 拉取当前运行 env 中配置的模型。
- 确认 `OLLAMA_BASE_URL=http://localhost:11434`。
- 如果在容器或远程环境运行，`localhost` 可能不是 Ollama 所在机器，需要改为可访问地址。

## 10. 前端访问后端失败

现象：

- 浏览器控制台出现网络错误。
- 开发代理没有转发到后端。
- 401 后跳转登录页。

处理：

- 一键启动时，`start.py` 会自动注入 `VITE_BACKEND_TARGET`。
- 前端单独启动时，检查 `front/.env`。
- 确认后端正在运行，且端口与 `VITE_BACKEND_TARGET` 一致。
- 统一启动时检查 `config/.env` 的 `CORS_ALLOW_ORIGINS`；后端单独启动时检查 `backend/.env`。
- 401 通常表示 JWT 过期、未登录或 Token 已加入黑名单，重新登录即可。

## 11. 端口被占用

现象：

- `Address already in use`
- `start.py` 自动选择了新的端口。

处理：

- 默认 `STRICT_PORTS=false` 时，脚本会自动尝试后续可用端口。
- 如果希望端口冲突时直接失败，设置 `STRICT_PORTS=true` 或传入 `--strict-ports`。
- Windows 可查看占用进程：

```powershell
netstat -ano | findstr :10000
```

## 12. 会话、测评或导图数据异常

处理：

- 确认当前请求携带 `Authorization: Bearer <token>`。
- 确认数据库连接正常。
- 确认业务查询按当前用户隔离，不要手动复用其他用户的 ID。
- 对于本地开发库，可重建数据库或清空 `public` schema，再启动后端自动创建当前表结构；`SEED_TEST_USER=true` 时会创建 `admin/admin1234` 便于验证。

## 13. 日志和调试

- 后端日志目录：`backend/logs/`。
- 前端日志：浏览器控制台。
- 健康检查：

```text
GET /health/live
GET /health/ready
```

- 交互式 API 文档：

```text
http://127.0.0.1:10000/docs
```

## 14. 最小自检命令

```powershell
cd backend
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe -c "from main import app; print(len(app.openapi().get('paths', {})))"
.venv\Scripts\python.exe -m pytest test\test_enterprise_contracts.py
```

```bash
cd front
npm run build
```

---

[返回首页](../README.md)
