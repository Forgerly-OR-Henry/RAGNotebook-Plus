# 项目文件结构说明

本文用树状结构记录当前项目目录和每个文件的作用。真实运行配置 `config/.env`、真实模型密钥 `config/apikey.txt`、依赖目录、构建产物、缓存和运行时数据由 `.gitignore` 排除；其中 `config/.env` 和 `config/apikey.txt` 虽不提交，但属于项目运行入口，仍在结构中记录。

```text
RAGNotebook/
├── .gitignore                                      # Git 忽略规则，排除真实配置、密钥、虚拟环境、依赖、构建产物、模型缓存和运行时数据。
├── LICENSE                                         # MIT License 文本。
├── README.md                                       # 面向使用者的项目介绍、快速开始、配置概览、技术栈和简化结构说明。
├── docker-compose.yml                              # 本地 PostgreSQL + pgvector 服务定义，读取 config/.env 中的数据库环境变量。
├── start.py                                        # 一键启动脚本；创建/读取 config/.env，解析文件型密钥，检查依赖，启动数据库服务、后端和前端。
│
├── config/                                         # 本地启动配置目录；真实配置和密钥被 Git 忽略。
│   ├── .env                                        # 本地真实运行配置，保存端口、数据库、模型、JWT、限流等配置；不提交。
│   ├── .env.example                                # 主配置模板；start.py 在缺少 config/.env 时从它复制。
│   ├── apikey.txt                                  # 本地真实模型 API Key 文件；通常由 ALIYUN_ACCESS_KEY_SECRET=apikey.txt 引用；不提交。
│   └── apikey.txt.example                          # API Key 文件模板，只保留占位内容。
│
├── backend/                                        # FastAPI 后端、数据库迁移、测试和 API 快照。
│   ├── .python-version                             # 后端 Python 版本提示文件，供版本管理工具识别。
│   ├── alembic.ini                                 # Alembic 配置入口；迁移运行时数据库 URL 会由 config/.env 覆盖。
│   ├── openapi.json                                # 当前后端 API 的静态 OpenAPI 快照。
│   ├── pyproject.toml                              # 后端项目元数据、依赖和测试配置。
│   ├── requirements.txt                            # pip 依赖清单，供非 uv 环境安装后端依赖。
│   │
│   ├── alembic/                                    # Alembic 数据库迁移目录。
│   │   ├── env.py                                  # Alembic 运行环境；加载 config/.env，导入 ORM 模型，配置 public schema 迁移。
│   │   └── versions/                               # 迁移版本脚本目录。
│   │       ├── 20260618_0001_initial_enterprise_postgres.py  # 初始 PostgreSQL 迁移，创建用户、笔记、会话、回顾、测评、导图和运行态表。
│   │       ├── 20260621_0002_pgvector_store.py     # 旧 pgvector 迁移，创建历史向量切片和知识库 MD5 去重结构。
│   │       └── 20260622_0003_domain_index_knowledge_documents.py  # 领域化索引迁移，创建 knowledge_documents 和 index_chunks，并从旧向量表回填。
│   │
│   ├── src/                                        # 后端源码根目录，采用扁平 MVC 分层。
│   │   ├── main.py                                 # FastAPI 应用入口；注册 controllers.routers、中间件、CORS、静态媒体、异常处理和生命周期。
│   │   ├── ai/                                     # AI 编排层。
│   │   │   ├── agent/                              # LangChain Agent 工具、流式执行和中间件。
│   │   │   └── rag/                                # RAG 问答编排、文档处理、检索器、重排序、SSE 和历史向量兼容层。
│   │   ├── config/                                 # 后端 YAML/JSON 配置目录。
│   │   │   ├── agent.yaml                          # Agent 配置文件。
│   │   │   ├── prompt.yaml                         # Prompt 类型到 prompt 文件的映射配置。
│   │   │   ├── rag.yaml                            # 旧 RAG 配置占位说明；模型配置已迁移到 config/.env。
│   │   │   ├── uvicorn_log_config.json             # Uvicorn 日志格式和级别配置。
│   │   │   └── vector_store.yaml                   # 知识库文件类型、切片大小、重叠长度、召回数量和数据路径配置。
│   │   ├── controllers/                            # FastAPI 控制器层，只负责参数、鉴权、限流、响应封装和流式响应。
│   │   │   ├── chat_controller.py                  # 聊天、Agent 流式问答、RAG 查询、会话和重排序路由。
│   │   │   ├── health_controller.py                # 存活检查和就绪检查路由。
│   │   │   ├── knowledge_controller.py             # 知识库文档资源 API，按 document_id 上传、查询、删除。
│   │   │   ├── mindmap_controller.py               # 思维导图生成、查询、更新和导出路由。
│   │   │   ├── note_controller.py                  # 笔记 CRUD、文件导入、搜索、批量操作、补全、写作辅助、关联和导出路由。
│   │   │   ├── note_template_controller.py         # 笔记模板列表、创建、更新、删除和排序路由。
│   │   │   ├── quick_test_controller.py            # 快速测试创建、答题、查询和结束路由。
│   │   │   ├── review_controller.py                # 每日回顾列表、标记完成和生成回顾问题路由。
│   │   │   └── user_controller.py                  # 登录、注册、重置密码、刷新 Token、用户资料、登出和头像上传路由。
│   │   ├── core/                                   # 通用核心能力：响应、异常、日志、限流和后台初始化。
│   │   ├── db/                                     # 数据库连接、自动迁移和测试用户初始化。
│   │   ├── models/                                 # SQLAlchemy ORM 模型。
│   │   ├── prompt/                                 # LLM 提示词模板目录。
│   │   ├── repositories/                           # 仓储和基础设施适配层，封装 pgvector、运行态存储、用户仓储和文档解析。
│   │   ├── schemas/                                # Pydantic 请求/响应模型，按业务拆分。
│   │   ├── services/                               # 业务服务层，封装笔记、模板、回顾、测评、导图、知识库、用户和来源聚合。
│   │   └── utils/                                  # 通用工具层，包括鉴权、配置加载、模型工厂、文件处理、路径和 prompt 加载。
│   │
│   └── test/                                       # 后端测试和演示数据夹具。
│       ├── test_demo_dataset.py                    # 演示数据 manifest 的结构和引用完整性测试。
│       ├── test_enterprise_contracts.py            # 企业版关键契约测试，覆盖配置、迁移和主要能力边界。
│       ├── test_knowledge_multimodal_defer.py      # 知识库上传阶段跳过视觉模型、按需保留多模态加载路径的回归测试。
│       ├── test_note_import.py                     # 笔记文件导入解析和保存非阻塞行为测试。
│       └── fixtures/
│           └── demo_dataset/
│               ├── manifest.json                   # 演示数据声明文件，定义用户、笔记、模板、知识库、会话、测评和导图夹具。
│               └── knowledge/
│                   ├── learning-workflow-checklist.txt        # 演示知识库文本文件：学习工作流检查清单。
│                   ├── pgvector-operations-runbook.md         # 演示知识库 Markdown 文件：pgvector 运维排查记录。
│                   └── ragnotebook-product-playbook.md        # 演示知识库 Markdown 文件：产品使用手册。
│
├── front/                                          # Vue3 + TypeScript 前端。
│   ├── .env.example                                # 前端独立启动时的环境变量模板；完整启动时由 config/.env 注入覆盖。
│   ├── .gitignore                                  # 前端目录局部忽略规则。
│   ├── README.md                                   # Vite/Vue 前端模板说明。
│   ├── eslint.config.js                            # 前端 ESLint 配置。
│   ├── index.html                                  # Vite HTML 入口。
│   ├── package-lock.json                           # npm 锁定文件。
│   ├── package.json                                # 前端依赖和 npm 脚本定义。
│   ├── postcss.config.js                           # PostCSS 配置，加载 Tailwind CSS。
│   ├── tailwind.config.cjs                         # Tailwind 内容扫描和主题扩展配置。
│   ├── tsconfig.app.json                           # 前端应用 TypeScript 编译配置。
│   ├── tsconfig.json                               # TypeScript 配置聚合入口。
│   ├── tsconfig.node.json                          # Node/Vite 配置文件 TypeScript 编译配置。
│   ├── vite.config.ts                              # Vite 开发服务器、代理目标、知识库长上传代理和构建配置。
│   ├── public/
│   │   └── icon.png                                # 前端静态图标资源。
│   └── src/                                        # 前端源码。
│       ├── App.vue                                 # Vue 根组件，承载 RouterView。
│       ├── index.css                               # 全局样式、Tailwind 引入和应用主题样式。
│       ├── main.ts                                 # Vue 应用入口，注册 Pinia 和 Router。
│       ├── types/
│       │   └── api.ts                              # 前端 API 类型定义，覆盖用户、笔记、知识库、聊天、回顾、测评和导图。
│       ├── api/                                    # 后端请求封装。
│       │   ├── auth.ts                             # 登录、注册、刷新 Token、用户资料、登出和头像上传请求封装。
│       │   ├── chat.ts                             # 聊天和 RAG 请求封装。
│       │   ├── client.ts                           # Axios 实例、基础 URL、超时、JWT 注入和 401 处理。
│       │   ├── endpoints.ts                        # 后端 API 路径集中定义。
│       │   ├── knowledge.ts                        # 知识库 feature API 的兼容 re-export。
│       │   ├── mindmaps.ts                         # 思维导图生成、获取、更新和导出请求封装。
│       │   ├── noteTemplates.ts                    # 笔记模板请求封装。
│       │   ├── notes.ts                            # 笔记 feature API 的兼容 re-export。
│       │   ├── quickTest.ts                        # 快速测试创建、答题、查询和结束请求封装。
│       │   ├── review.ts                           # 回顾列表、标记完成和问题生成请求封装。
│       │   └── sessions.ts                         # 聊天会话列表、详情和删除请求封装。
│       ├── components/                             # 通用组件。
│       │   ├── AppShell.vue                        # 登录后主布局，包含侧边导航、页面标题和退出登录入口。
│       │   └── RichEditor.vue                      # Tiptap 富文本编辑器组件，使用 v-model 同步笔记正文。
│       ├── router/
│       │   └── index.ts                            # Vue Router 路由表和登录态守卫。
│       ├── stores/                                 # Pinia 状态管理。
│       │   ├── useLanguageStore.ts                 # 语言偏好状态。
│       │   ├── useSessionStore.ts                  # 会话状态，用于保存当前会话标识。
│       │   ├── useThemeStore.ts                    # 主题状态，管理明暗主题偏好。
│       │   └── useUserStore.ts                     # 用户状态，管理 JWT、本地用户信息和登录状态。
│       ├── features/                               # 前端按业务能力收拢的 feature 模块。
│       │   ├── knowledge/
│       │   │   └── api.ts                          # 知识库 document_id API，请求 /knowledge/documents。
│       │   ├── notes/
│       │   │   └── api.ts                          # 笔记 API 封装。
│       │   └── sources/
│       │       └── index.ts                        # 来源类型导出。
│       └── views/                                  # 页面组件。
│           ├── AboutView.vue                       # 关于页面。
│           ├── ChatView.vue                        # AI 聊天页面，发起问答并展示消息。
│           ├── KnowledgeView.vue                   # 知识库管理页面，支持拖拽/选择流式上传 PDF、TXT、Markdown、Word、PPT 文档，展示文档列表、点击预览内容并支持删除和清空。
│           ├── LoginView.vue                       # 登录页面。
│           ├── MindMapView.vue                     # 思维导图页面，选择来源、生成图谱并渲染 Vue Flow。
│           ├── NoteEditorView.vue                  # 笔记编辑页面，创建、编辑或删除标题、正文和分类。
│           ├── NoteListView.vue                    # 笔记列表页面，展示笔记并支持搜索、分类筛选、新建、文件导入、删除和卡片分类标识。
│           ├── ProfileView.vue                     # 用户资料页面。
│           ├── QuickTestView.vue                   # 快速测试页面，选择来源、答题、查看反馈和总结。
│           ├── RegisterView.vue                    # 注册页面。
│           ├── ReviewView.vue                      # 每日回顾页面。
│           ├── SessionsView.vue                    # 聊天会话列表页面。
│           └── SettingsView.vue                    # 设置页面，管理主题和语言偏好。
│
├── docs/                                           # 项目文档。
│   ├── developer_guide.md                          # 开发者指南，记录架构、生命周期、数据模型、接口分组和维护约定。
│   ├── file.md                                     # 当前文件，树状记录项目结构和每个文件的作用。
│   ├── modelscope_model.md                         # 重排序模型下载、路径配置和启动加载说明。
│   ├── project_develop.md                          # 相对上游项目的改进说明。
│   └── troubleshooting.md                          # 常见启动、数据库、模型、上传和前端代理问题排查。
│
├── images/                                         # README 和文档使用的截图资源。
│   ├── aichat.png                                  # README 的 AI 聊天界面截图。
│   ├── editor_note.png                             # README 的笔记编辑界面截图。
│   ├── knowledge_manager.png                       # README 的知识库界面截图。
│   ├── note.png                                    # README 的笔记列表界面截图。
│   └── text_spliter.png                            # README 或说明文档使用的文本切片示意截图。
│
└── scripts/                                        # 辅助脚本目录。
    ├── seed_demo_data.py                           # 演示数据导入脚本；校验 manifest，写入用户/笔记/模板/会话/测评/导图，并同步向量。
    ├── download_reranker_model/
    │   ├── download_reranker_model.bat             # Windows 下下载重排序模型的批处理入口。
    │   └── download_reranker_model.py              # 从 ModelScope 下载 BAAI/bge-reranker-v2-m3 并提示更新 config/.env。
    └── postgresql/
        ├── install_pgvector_windows.bat            # Windows 下安装 pgvector 的辅助批处理脚本。
        └── pg.sh                                   # Linux PostgreSQL 管理脚本，包含安装、服务、用户/库、扩展和备份等操作。
```
