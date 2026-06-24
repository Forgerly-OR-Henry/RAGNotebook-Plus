# 项目文件结构说明

本文用树状结构记录当前项目目录和每个文件的作用。统一启动配置 `config/.env`、后端单独启动配置 `backend/.env`、前端单独启动配置 `front/.env`、真实模型密钥 `config/apikey.txt`、依赖目录、构建产物、缓存和运行时数据由 `.gitignore` 排除；其中 `config/.env` 和 `config/apikey.txt` 虽不提交，但属于项目运行入口，仍在结构中记录。

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
├── backend/                                        # FastAPI 后端、数据库初始化、测试和 API 快照。
│   ├── .python-version                             # 后端 Python 版本提示文件，供版本管理工具识别。
│   ├── .env.example                                # 后端手动启动配置模板；真实 backend/.env 不提交。
│   ├── openapi.json                                # 当前后端 API 的静态 OpenAPI 快照。
│   ├── pyproject.toml                              # 后端项目元数据、依赖和测试配置。
│   ├── requirements.txt                            # pip 依赖清单，供非 uv 环境安装后端依赖。
│   │
│   ├── config/                                     # 后端 YAML/JSON 配置目录，位于源码包之外。
│   │   ├── agent.yaml                              # Agent 配置文件。
│   │   ├── rag.yaml                                # 旧 RAG 配置占位说明；模型配置已迁移到 env。
│   │   └── uvicorn_log_config.json                 # Uvicorn 日志格式和级别配置。
│   │
│   ├── src/                                        # 后端源码根目录，按 agent 与 mvc 两个主域组织。
│   │   ├── main.py                                 # FastAPI 应用入口；注册 mvc.controllers.routers、中间件、CORS、异常处理和生命周期。
│   │   ├── agent/                                  # 智能能力层，负责 LLM、RAG、Prompt、模型和索引。
│   │   │   ├── indexing/                           # 文档解析、统一索引仓储和 pgvector 写入/检索能力。
│   │   │   ├── models/                             # Chat、Embedding、Vision 模型工厂。
│   │   │   ├── prompts/                            # LLM 提示词模板和 Prompt registry。
│   │   │   ├── rag/                                # RAG 问答编排、文档处理、检索器、重排序和 SSE 模型。
│   │   │   ├── runtime/                            # LangChain Agent 工具、流式执行和中间件。
│   │   │   └── vision/                             # 多模态视觉模型调用服务。
│   │   ├── mvc/                                    # MVC 应用层，负责 API、业务、数据库和事务。
│   │   │   ├── agent_gateway/                      # MVC 调用 agent 的唯一入口。
│   │   │   ├── controllers/                        # FastAPI 控制器层，只负责参数、鉴权、限流、响应封装和流式响应。
│   │   │   ├── models/                             # SQLAlchemy ORM 模型。
│   │   │   ├── repositories/                       # MVC 仓储层，封装运行态存储和用户仓储。
│   │   │   ├── schemas/                            # Pydantic 请求/响应模型，按业务拆分。
│   │   │   └── services/                           # 业务服务层，封装笔记、模板、测评、导图、知识库、快速测验、用户和来源聚合。
│   │   ├── core/                                   # 通用核心能力：响应、异常、日志、限流和后台初始化。
│   │   ├── db/                                     # 数据库连接、新库/空库建表和测试用户初始化。
│   │   └── utils/                                  # 通用工具层，包括鉴权、配置加载、文件处理和路径工具。
│   │
│   └── test/                                       # 后端契约测试、服务测试和回归测试。
│       ├── test_auth_utils.py                      # 密码哈希、JWT 创建和鉴权工具测试。
│       ├── test_background_init_status.py          # 后台初始化状态和健康检查响应测试。
│       ├── test_chat_projects_contracts.py         # 聊天项目、项目文件和项目会话契约测试。
│       ├── test_dashscope_embeddings.py            # DashScope 嵌入模型封装测试。
│       ├── test_domain_refactor_contracts.py       # 分层重构后的领域契约测试。
│       ├── test_enterprise_contracts.py            # 企业版关键能力边界测试。
│       ├── test_env_loader.py                      # 环境变量加载和配置注入测试。
│       ├── test_file_handler.py                    # 文件类型识别和解析器测试。
│       ├── test_health_readiness.py                # 存活、就绪和依赖状态测试。
│       ├── test_knowledge_folders.py               # 知识库文件夹接口和树结构测试。
│       ├── test_knowledge_ingestion_service.py     # 知识库上传中断、半成品清理和摄入流程测试。
│       ├── test_knowledge_multimodal_defer.py      # 知识库上传阶段跳过视觉模型、按需保留多模态加载路径的回归测试。
│       ├── test_logging_filters.py                 # 日志过滤规则测试。
│       ├── test_note_folders.py                    # 笔记文件夹接口和树结构测试。
│       ├── test_note_import.py                     # 笔记文件导入解析和保存非阻塞行为测试。
│       ├── test_note_routes.py                     # 笔记路由、批量操作和边界行为测试。
│       ├── test_note_template_routes.py            # 笔记模板路由测试。
│       ├── test_quiz_generation.py                 # 快速测验生成请求、来源收集和空内容错误契约测试。
│       ├── test_start_readiness.py                 # 一键启动前置检查和就绪逻辑测试。
│       ├── test_startup_config.py                  # FastAPI startup 配置和初始化顺序测试。
│       ├── test_storage_service.py                 # 本地/SFTP 文件存储服务测试。
│       └── test_user_profile_contracts.py          # 用户资料、密码和头像契约测试。
│
├── front/                                          # Vue 3 + TypeScript 前端。
│   ├── .env.example                                # 前端独立启动时的环境变量模板；统一启动时由 config/.env 注入覆盖。
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
│       │   └── api.ts                              # 前端 API 类型定义，覆盖用户、笔记、知识库、聊天、测评和导图。
│       ├── api/                                    # 后端请求封装。
│       │   ├── auth.ts                             # 登录、注册、刷新 Token、用户资料、登出、密码和头像上传请求封装。
│       │   ├── authToken.ts                        # 访问 Token 本地读写和清理工具。
│       │   ├── chat.ts                             # 聊天、RAG、项目会话和快速测验生成请求封装。
│       │   ├── client.ts                           # Axios 实例、基础 URL、超时、JWT 注入和 401 处理。
│       │   ├── endpoints.ts                        # 后端 API 路径集中定义。
│       │   ├── health.ts                           # 健康检查和后台初始化状态请求封装。
│       │   ├── knowledge.ts                        # 知识库 feature API 的兼容 re-export。
│       │   ├── localPrefs.ts                       # 本地偏好读写工具。
│       │   ├── mindmaps.ts                         # 思维导图生成、获取、更新和导出请求封装。
│       │   ├── notes.ts                            # 笔记 feature API 的兼容 re-export。
│       │   ├── noteTemplates.ts                    # 笔记模板请求封装。
│       │   ├── projects.ts                         # 聊天项目、项目文件和项目会话请求封装。
│       │   ├── quickTest.ts                        # 连续问答式快速测试创建、答题、查询和结束请求封装。
│       │   ├── sessions.ts                         # 聊天会话列表、详情和删除请求封装。
│       │   └── stream.ts                           # SSE / fetch 流式响应读取工具。
│       ├── components/                             # 通用组件。
│       │   ├── AppDialogHost.vue                   # 全局确认/提示对话框挂载组件。
│       │   ├── AppShell.vue                        # 登录后主布局，包含侧边导航、页面标题和退出登录入口。
│       │   ├── BatchActionBar.vue                  # 笔记批量操作栏，支持置顶、分类、移动、导图、下载和删除。
│       │   ├── CategoryManageDialog.vue            # 笔记分类管理弹窗。
│       │   ├── ConfirmDialog.vue                   # 通用确认弹窗。
│       │   ├── KnowledgeDocumentPreview.vue        # 知识库文档详情和解析内容预览组件。
│       │   ├── MarkdownEditor.vue                  # Markdown 编辑器组件。
│       │   ├── MarkdownRenderer.vue                # Markdown 安全渲染组件。
│       │   ├── MindMapCanvas.vue                   # 思维导图树状画布组件，支持拖拽、缩放、重置和复制大纲。
│       │   ├── MindMapModal.vue                    # 批量选中笔记后生成导图的弹窗入口。
│       │   ├── MindMapTreeNode.vue                 # 思维导图递归树节点组件。
│       │   ├── OutlinePanel.vue                    # 笔记大纲面板。
│       │   ├── RelatedFragments.vue                # 笔记相关片段和知识库关联推荐组件。
│       │   ├── RichEditor.vue                      # Tiptap 富文本编辑器组件，使用 v-model 同步笔记正文。
│       │   └── TagInput.vue                        # 标签输入组件。
│       ├── composables/
│       │   └── useAppDialog.ts                     # 全局确认/提示对话框状态和调用方法。
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
│       │       ├── folderTree.ts                   # 笔记/知识库来源文件夹树构建工具。
│       │       └── index.ts                        # 来源类型导出。
│       ├── utils/
│       │   └── markdown.ts                         # Markdown 清理、转换和渲染辅助工具。
│       └── views/                                  # 页面组件。
│           ├── AboutView.vue                       # 关于页面。
│           ├── ChatView.vue                        # AI 聊天页面，发起问答并展示消息。
│           ├── KnowledgeDetailView.vue             # 知识库文档详情页，展示解析预览、切片和元数据。
│           ├── KnowledgeView.vue                   # 知识库管理页面，支持拖拽/选择流式上传 PDF、TXT、Markdown、Word、PPT 文档，展示文档列表、预览入口、删除和清空。
│           ├── LoginView.vue                       # 登录页面。
│           ├── MindMapView.vue                     # 思维导图页面，支持多选笔记或知识库来源，生成可拖拽缩放的树状导图。
│           ├── NoteEditorView.vue                  # 笔记编辑页面，创建、编辑或删除标题、正文和分类。
│           ├── NoteListView.vue                    # 笔记列表页面，展示笔记并支持搜索、分类筛选、新建、文件导入、删除和卡片分类标识。
│           ├── ProfileView.vue                     # 用户资料页面。
│           ├── QuickTestView.vue                   # 快速测试页面，选择笔记/知识库来源，生成选择题测验、答题并查看得分解析。
│           ├── RegisterView.vue                    # 注册页面。
│           ├── SessionsView.vue                    # 聊天会话列表页面。
│           └── SettingsView.vue                    # 设置页面，管理主题和语言偏好。
│
├── docs/                                           # 项目文档。
│   ├── developer_guide.md                          # 开发者指南，记录架构、生命周期、数据模型、接口分组和维护约定。
│   ├── enterprise_development_document.md          # 面向答辩、课程交付和团队协作的企业级开发总览文档。
│   ├── file.md                                     # 当前文件，树状记录项目结构和每个文件的作用。
│   ├── modelscope_model.md                         # 重排序模型下载、路径配置和启动加载说明。
│   ├── project_develop.md                          # 相对上游项目的改进说明。
│   └── troubleshooting.md                          # 常见启动、数据库、模型、上传和前端代理问题排查。
│
├── test_data/                                      # 手工上传和解析验证用的本地测试数据集。
│   ├── realistic_user_dataset/                     # 真实风格多格式资料集，适合验证跨来源检索、来源核对和资料复用。
│   │   └── README.md                               # 数据集背景、文件类型覆盖、文件清单和建议使用方式。
│   └── upload_test_dataset/                        # 小型上传测试数据集，覆盖 TXT / PDF / MD / DOCX / PPTX 解析链路。
│
└── scripts/                                        # 辅助脚本目录。
    ├── download_reranker_model/
    │   ├── download_reranker_model.bat             # Windows 下下载重排序模型的批处理入口。
    │   └── download_reranker_model.py              # 从 ModelScope 下载 BAAI/bge-reranker-v2-m3 并提示更新当前运行 env。
    ├── postgresql/
    │   ├── install_pgvector_windows.bat            # Windows 下安装 pgvector 的辅助批处理脚本。
    │   └── pg.sh                                   # Linux PostgreSQL 管理脚本，包含安装、服务、用户/库、扩展和备份等操作。
    └── user.sh                                     # 用户相关的本地辅助脚本。
```
