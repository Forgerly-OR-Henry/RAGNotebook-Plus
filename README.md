# RAGNotebook 改进版 / 云笺集

云笺集是基于 [RMA-MUN/RAGNotebook](https://github.com/RMA-MUN/RAGNotebook) 改进的智能笔记与知识库系统。项目保留原有 RAG Notebook 的核心思路，并把工程底座升级为 **FastAPI + PostgreSQL + pgvector + Vue3 + TypeScript**，用于管理笔记、知识库、测评和思维导图。

> 本仓库为二次开发改进版。感谢原作者 RMA-MUN 的开源工作；项目继续遵循 MIT License。

## 目录

- [本改进版说明](#本改进版说明)
- [核心能力](#核心能力)
- [项目演示](#项目演示)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [开发文档](#开发文档)
- [故障排除](#故障排除)
- [License](#license)

## 本改进版说明

本项目不是单纯的 RAG 问答 demo，而是围绕“笔记写完后如何持续复用”做的一套个人知识管理工具。相对上游项目，本改进版重点调整如下：

| 方向 | 当前改进版 |
| --- | --- |
| 数据底座 | PostgreSQL 统一承载用户、文档元数据、笔记、会话、测评、导图、运行态数据 |
| 向量检索 | PostgreSQL pgvector 存储知识库与笔记向量，统一用户隔离 |
| 文件存储 | 统一 StorageService 管理 Markdown 笔记、知识库原文件、附件和头像，支持本机目录与 SFTP |
| 数据库初始化 | 后端启动仅支持新库/空库，自动创建当前表结构、pgvector 扩展和索引表 |
| 前端 | Vue3 + TypeScript + Vite + Pinia |
| 启动方式 | 根目录 `start.py` 统一读取 `config/.env`，启动数据库、后端和前端；数据库初始化由后端 startup 负责 |
| 新增能力 | NotebookLM 风格快速测试、交互式思维导图、统一运行态表、OpenAPI 快照 |

完整改进说明见 [docs/project_develop.md](./docs/project_develop.md)。

## 核心能力

- **笔记管理**：Markdown/Tiptap 编辑、分类、标签、置顶、分页、批量操作和 Markdown 导出。
- **智能标签**：保存笔记后可由 LLM 异步生成标签和分类。
- **语义搜索**：笔记和知识库切片进入 `index_chunks`，支持向量检索。
- **RAG 知识库**：支持 TXT / PDF / MD / PPTX / DOCX 上传，原文件保持上传格式，解析后切片、向量化、详情和切片查看。
- **AI 问答**：Agent 流式对话，结合知识库与笔记检索结果生成回答。
- **AI 写作辅助**：内联补全、续写、扩写、摘要和跨源关联推荐。
- **快速测试**：从笔记、知识库或混合来源生成连续问答、反馈和总结。
- **思维导图**：从笔记或知识库生成交互式树状导图，支持拖拽缩放、大纲复制、JSON 和 Mermaid 导出。
- **用户隔离**：关系数据和向量数据都以 `user_id` 作为访问边界。
- **运行态治理**：Token 撤销、限流桶、短期缓存等写入 PostgreSQL。

## 项目演示

| 功能模块 | 界面展示 |
| --- | :--- |
| 笔记编辑 | ![笔记编辑](./images/editor_note.png) |
| 笔记列表 | ![笔记列表](./images/note.png) |
| AI 聊天 | ![AI 聊天](./images/aichat.png) |
| 知识库 | ![知识库](./images/knowledge_manager.png) |

## 快速开始

### 环境要求

| 环境 | 推荐版本 |
| --- | --- |
| Python | 3.12+ |
| Node.js | 16+ |
| Docker | 可运行 Compose |
| PostgreSQL | 16，需 pgvector 扩展 |

如果本机使用 Docker，项目默认通过 `docker-compose.yml` 启动 `pgvector/pgvector:pg16`。

### 克隆项目

```bash
git clone https://github.com/RMA-MUN/RAGNotebook.git
cd RAGNotebook
```

### 一键启动

首次启动建议让脚本安装依赖：

```bash
python start.py --install
```

之后可直接启动开发栈：

```bash
python start.py
```

`start.py` 会执行以下工作：

1. 如果 `config/.env` 不存在，从 `config/.env.example` 创建。
2. 如果配置了 `ALIYUN_ACCESS_KEY_SECRET=apikey.txt` 且文件不存在，创建被 Git 忽略的 `config/apikey.txt`。
3. 读取 `config/.env`，并注入给 PostgreSQL、FastAPI 和 Vite。
4. 通过 Docker Compose 启动 PostgreSQL。
5. 启动后端；后端 startup 会在新库/空库中创建当前表结构和 pgvector 索引表。
6. 等后端后台初始化完成后启动前端开发服务。

常用参数：

```bash
python start.py --backend-only
python start.py --frontend-only
python start.py --skip-db
python start.py --strict-ports
```

默认地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://127.0.0.1:10100` |
| 后端 | `http://127.0.0.1:10000` |
| API 文档 | `http://127.0.0.1:10000/docs` |

### 手动启动

后端：

```powershell
cd backend
.venv\Scripts\python.exe src\main.py
```

前端：

```bash
cd front
npm install
npm run dev
```

数据库：

```bash
docker compose up -d postgres
```

## 配置说明

配置读取边界：

- 使用 `start.py` 统一启动时，只读取 `config/.env`，并把配置注入给 PostgreSQL、后端和前端。
- 单独启动后端时，只读取 `backend/.env`；`backend/.env.example` 是模板。
- 单独启动前端时，只读取 `front/.env`；`front/.env.example` 是模板。

最小配置示例：

```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=10000
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=10100

DATABASE_URL=postgresql+asyncpg://rag:rag@localhost:5432/rag_notebook
POSTGRES_USER=rag
POSTGRES_PASSWORD=rag
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=rag_notebook

ALIYUN_ACCESS_KEY_SECRET=apikey.txt
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OLLAMA_BASE_URL=http://localhost:11434

LLM_TYPE=ALIYUN
CHAT_MODEL_NAME=qwen3-max
OLLAMA_MODEL_NAME=qwen3.5:0.8b

EMBED_MODEL_TYPE=ALIYUN
ALIYUN_EMBED_MODEL_NAME=text-embedding-v4
TEXT_EMBEDDING_MODEL_NAME=qwen3-embedding:0.6b
EMBEDDING_DIM=1024

VISION_MODEL_TYPE=ALIYUN
VISION_CHAT_MODEL_NAME=qwen-vl-max
VISION_OLLAMA_MODEL_NAME=qwen-vl:7b

RERANKER_MODEL_PATH=D:\Hugging_Face\models\bge-reranker-v2-m3
RATE_LIMIT_ENABLED=false
SEED_TEST_USER=true
SECRET_KEY=change-me
ALGORITHM=HS256
```

`SEED_TEST_USER=true` 仅面向本地开发，会在空库中确保 `admin/admin1234` 测试用户存在；非本地环境建议设为 `false`。

真实模型 API Key 请写入 `config/apikey.txt`，不要提交，文件内只放一行 key：

```txt
your_api_key_here
```

知识库文件类型白名单在 `backend/src/mvc/services/knowledge_service.py`，切片默认值在 `backend/src/agent/rag/text_spliter.py`。持久文件位置由 `FILE_STORAGE_*` 环境变量控制。

重排序模型配置见 [docs/modelscope_model.md](./docs/modelscope_model.md)。

## 技术栈

### 后端

| 技术 | 说明 |
| --- | --- |
| FastAPI | 异步 API 服务 |
| LangChain | Agent、工具调用、模型接入和 RAG 编排 |
| PostgreSQL | 关系数据、运行态数据、会话历史 |
| pgvector | 知识库和笔记向量检索 |
| SQLAlchemy + asyncpg | 异步数据库访问 |
| DashScope / Ollama | 云端或本地模型 |
| sentence-transformers | 重排序模型加载 |

### 前端

| 技术 | 说明 |
| --- | --- |
| Vue3 | 应用框架 |
| TypeScript | 类型约束 |
| Vite | 开发与构建 |
| Pinia | 状态管理 |
| Vue Router | 路由与登录态守卫 |
| Tailwind CSS | 页面样式 |
| Tiptap | 笔记编辑器 |
| 自定义树状画布 | 思维导图渲染、拖拽缩放和大纲复制 |
| Axios | HTTP 请求 |

## 项目结构

```text
├── backend/
│   ├── src/                        # FastAPI 应用、业务模块、RAG 和数据库代码
│   ├── test/                       # 后端契约测试和演示数据夹具
│   └── openapi.json                # 当前 API 快照
├── front/
│   ├── src/                        # Vue3 页面、组件、API 封装、路由和状态
│   └── package.json                # 前端依赖与脚本
├── config/                         # 本地启动配置模板；真实 .env 和 apikey 被忽略
├── docs/                           # 开发、排错、模型和逐文件结构文档
├── scripts/                        # 演示数据、模型下载和 PostgreSQL 辅助脚本
├── images/                         # README 截图
├── docker-compose.yml
└── start.py
```

详细树状结构和逐文件用途见 [docs/file.md](./docs/file.md)。

## API 文档

- 静态 OpenAPI 快照：[backend/openapi.json](./backend/openapi.json)
- 启动服务后的交互式文档：`http://127.0.0.1:${BACKEND_PORT}/docs`

当前主要接口分组：

| 前缀 | 说明 |
| --- | --- |
| `/user` | 登录、注册、刷新 Token、登出、资料更新 |
| `/file` | 头像等文件上传 |
| `/chat` | Agent 问答、RAG 查询、会话、重排序 |
| `/knowledge` | 知识库上传、列表、详情、切片、图片和去重记录 |
| `/note` | 笔记 CRUD、搜索、批量操作、补全、写作辅助 |
| `/note-template` | 笔记模板 |
| `/quick-test` | 快速测试 |
| `/mindmaps` | 思维导图 |
| `/health` | 存活和就绪检查 |

## 开发文档

- [开发者指南](./docs/developer_guide.md)：架构、数据流、扩展路径和维护约定。
- [文件结构说明](./docs/file.md)：用树状结构逐文件记录项目结构和每个文件的作用。
- [改进说明](./docs/project_develop.md)：本改进版相对上游的主要变化。
- [模型配置](./docs/modelscope_model.md)：重排序模型下载、自动加载和环境变量。
- [故障排除](./docs/troubleshooting.md)：常见启动、数据库、模型、上传和前端代理问题。

## 故障排除

常见入口：

- API Key 错误：统一启动检查 `config/.env`，后端单独启动检查 `backend/.env`，确认 `ALIYUN_ACCESS_KEY_SECRET` 指向有效 key 文件。
- 数据库连接失败：确认 `docker compose up -d postgres` 已启动，且 `DATABASE_URL` 与 `POSTGRES_*` 一致。
- pgvector 初始化失败：确认数据库可执行 `CREATE EXTENSION vector`，本地建议使用默认 Compose 镜像。
- 旧数据库无法启动：当前版本只支持新库/空库，请清空 `public` schema 或重建 `POSTGRES_DB`。
- 向量维度不匹配：确认当前运行 env 的 `EMBEDDING_DIM` 与当前嵌入模型输出一致。
- 前端无法访问后端：检查 `VITE_BACKEND_TARGET`、后端端口和 `CORS_ALLOW_ORIGINS`。

更多内容见 [docs/troubleshooting.md](./docs/troubleshooting.md)。

## License

本项目基于 MIT License 开源，详见 [LICENSE](./LICENSE)。二次开发版本保留对上游 [RMA-MUN/RAGNotebook](https://github.com/RMA-MUN/RAGNotebook) 的致谢。

## Star History

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=RMA-MUN/RAGNotebook&type=Date&theme=dark" />
  <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=RMA-MUN/RAGNotebook&type=Date" />
  <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=RMA-MUN/RAGNotebook&type=Date" />
</picture>
