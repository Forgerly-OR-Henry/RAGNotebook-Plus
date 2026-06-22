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
│   │       └── 20260621_0002_pgvector_store.py     # pgvector 迁移，创建向量切片和知识库 MD5 去重相关结构。
│   │
│   ├── src/                                        # 后端源码根目录。
│   │   ├── main.py                                 # FastAPI 应用入口；注册路由、中间件、CORS、静态媒体、异常处理和生命周期。
│   │   ├── seed_templates.py                       # 默认笔记模板种子脚本，向数据库写入内置模板。
│   │   └── app/                                    # 后端应用包。
│   │       ├── __init__.py                         # app 包标识文件。
│   │       │
│   │       ├── agent/                              # LangChain Agent 工具与流式执行模块。
│   │       │   ├── __init__.py                     # Agent 包标识文件。
│   │       │   ├── agent.py                        # Agent 工厂和执行入口，提供普通响应与 SSE 流式响应。
│   │       │   ├── agent_middleware.py             # Agent 和模型调用前后的日志/钩子中间件。
│   │       │   └── agent_tools.py                  # Agent 可调用工具集合，包括 RAG、用户信息、笔记搜索、回顾、创建笔记和相关笔记查询。
│   │       │
│   │       ├── cache/                              # PostgreSQL 缓存封装。
│   │       │   ├── __init__.py                     # cache 包标识文件。
│   │       │   └── pg_cache_decorator.py           # PostgreSQL 缓存类和装饰器，用于按 key 缓存异步结果。
│   │       │
│   │       ├── config/                             # 后端 YAML/JSON 配置目录。
│   │       │   ├── agent.yaml                      # Agent 配置文件。
│   │       │   ├── prompt.yaml                     # Prompt 类型到 prompt 文件的映射配置。
│   │       │   ├── rag.yaml                        # 旧 RAG 配置占位说明；模型配置已迁移到 config/.env。
│   │       │   ├── uvicorn_log_config.json         # Uvicorn 日志格式和级别配置。
│   │       │   └── vector_store.yaml               # 知识库文件类型、切片大小、重叠长度、召回数量和数据路径配置。
│   │       │
│   │       ├── core/                               # 通用核心能力：响应、异常、日志、限流和后台初始化。
│   │       │   ├── __init__.py                     # core 包标识文件。
│   │       │   ├── background_init.py              # 后台初始化管理器，异步加载模型、pgvector 服务和重排序模型。
│   │       │   ├── failed_response.py              # 业务异常、HTTP 异常、校验异常、SQLAlchemy 异常和通用异常处理逻辑。
│   │       │   ├── failed_response_register.py     # 将统一异常处理器注册到 FastAPI app。
│   │       │   ├── logger_handler.py               # 后端日志器创建和格式配置。
│   │       │   ├── logging_filters.py              # 日志级别过滤器，支持按最大级别过滤输出。
│   │       │   ├── rate_limit.py                   # 限流依赖和限流中间件，使用 PostgreSQL 运行态表记录窗口计数。
│   │       │   └── success_response.py             # 成功响应统一包装函数。
│   │       │
│   │       ├── db/                                 # 数据库连接、自动迁移和运行态存储。
│   │       │   ├── __init__.py                     # db 包标识文件。
│   │       │   ├── db_config.py                    # 构建数据库 URL，创建 SQLAlchemy async engine/session，初始化表结构和测试用户。
│   │       │   ├── pg_auto_init.py                 # PostgreSQL 自动初始化入口；检测业务表，调用 Alembic 升级，输出诊断错误。
│   │       │   └── pg_runtime_store.py             # PostgreSQL 运行态存储，封装缓存、Token 黑名单、限流计数和过期清理。
│   │       │
│   │       ├── models/                             # SQLAlchemy ORM 模型。
│   │       │   ├── __init__.py                     # ORM 模型包标识文件。
│   │       │   ├── chat_history.py                 # 聊天会话和聊天消息 ORM 模型。
│   │       │   ├── mind_map.py                     # 思维导图 ORM 模型，保存图结构、来源和版本。
│   │       │   ├── note.py                         # 笔记 ORM 模型，保存标题、正文、分类、标签和置顶状态。
│   │       │   ├── note_template.py                # 笔记模板 ORM 模型，保存用户模板和默认模板。
│   │       │   ├── review_record.py                # 回顾记录 ORM 模型，保存复习次数、间隔和下一次回顾时间。
│   │       │   ├── runtime_state.py                # 运行态 ORM 模型，包括缓存、Token 黑名单和限流计数。
│   │       │   ├── study_test.py                   # 快速测试会话和每轮问答 ORM 模型。
│   │       │   └── user_model.py                   # 用户 ORM 模型、用户状态枚举和 UUID 生成函数。
│   │       │
│   │       ├── prompt/                             # LLM 提示词模板目录。
│   │       │   ├── auto_tag_prompt.txt             # 笔记自动标签和分类提示词。
│   │       │   ├── autocomplete_prompt.txt         # 笔记编辑自动补全提示词。
│   │       │   ├── main_prompt.txt                 # Agent 主提示词。
│   │       │   ├── rag_summarize.txt               # RAG 检索片段总结提示词。
│   │       │   ├── reorder_prompt.txt              # 重排序/片段判断提示词。
│   │       │   ├── report_prompt.txt               # 报告生成提示词。
│   │       │   ├── review_question_prompt.txt      # 回顾问题生成提示词。
│   │       │   └── write_assistant_prompt.txt      # 写作辅助、续写、扩写和摘要提示词。
│   │       │
│   │       ├── rag/                                # RAG 文档处理、向量库、检索、重排序和 SSE 进度模块。
│   │       │   ├── __init__.py                     # RAG 包标识文件。
│   │       │   ├── rag_service.py                  # RAG 问答编排服务，组织查询改写、检索、重排序和回答生成。
│   │       │   ├── reorder_service.py              # 重排序模型路径解析、下载检查和候选文档重排序服务。
│   │       │   ├── sse_models.py                   # 知识库处理 SSE 事件和切片结果数据结构。
│   │       │   ├── task_queue.py                   # 异步任务队列，用于知识库上传和切片进度推送。
│   │       │   ├── text_spliter.py                 # 异步文本切片器，按配置切分文档内容。
│   │       │   ├── vector_store.py                 # pgvector 存储服务，负责向量写入、检索、删除和用户隔离。
│   │       │   ├── document_handler/               # 文档处理子模块。
│   │       │   │   ├── __init__.py                 # 文档处理包标识文件。
│   │       │   │   └── processor.py                # 统一文件解析、切片、向量化和元数据生成流程。
│   │       │   ├── md5_manager/                    # 知识库文件去重记录子模块。
│   │       │   │   ├── __init__.py                 # MD5 管理包标识文件。
│   │       │   │   └── md5_store.py                # 知识库文件 MD5 去重记录读写封装。
│   │       │   └── retrievers/                     # 检索器子模块。
│   │       │       ├── __init__.py                 # 检索器包导出文件。
│   │       │       ├── empty_retriever.py          # 空检索器，用于无可用向量库时返回空结果。
│   │       │       └── hybrid_retriever.py         # pgvector 检索器和混合检索封装。
│   │       │
│   │       ├── router/                             # FastAPI 路由和部分路由级服务。
│   │       │   ├── __init__.py                     # router 包标识文件。
│   │       │   ├── chat.py                         # 聊天、Agent 流式问答、RAG 查询、会话和重排序 API 路由。
│   │       │   ├── chat_service.py                 # 聊天路由服务，封装会话列表、详情和删除逻辑。
│   │       │   ├── health.py                       # 存活检查和就绪检查路由。
│   │       │   ├── knowledge_router.py             # 知识库上传、流式处理、清理、列表、详情、切片、图片和 MD5 记录路由。
│   │       │   ├── knowledge_service.py            # 知识库业务服务，处理文件保存、切片、向量化、去重和进度状态。
│   │       │   ├── mindmap_router.py               # 思维导图生成、查询、更新和导出路由。
│   │       │   ├── note_router.py                  # 笔记 CRUD、搜索、批量操作、统计、补全、写作辅助、关联和导出路由。
│   │       │   ├── note_template_router.py         # 笔记模板列表、创建、更新、删除和排序路由。
│   │       │   ├── quick_test_router.py            # 快速测试创建、答题、查询和结束路由。
│   │       │   ├── review_router.py                # 每日回顾列表、标记完成和生成回顾问题路由。
│   │       │   └── user.py                         # 登录、注册、重置密码、刷新 Token、用户资料、登出和头像上传路由。
│   │       │
│   │       ├── schemas/                            # Pydantic 请求/响应模型。
│   │       │   ├── __init__.py                     # schemas 包标识文件。
│   │       │   ├── models.py                       # 业务 API 模型，覆盖聊天、知识库、笔记、模板、快速测试和思维导图。
│   │       │   └── user_schemas.py                 # 用户登录、注册、更新、Token 刷新和用户资料响应模型。
│   │       │
│   │       ├── services/                           # 业务服务层。
│   │       │   ├── __init__.py                     # 服务包入口，并提供会话管理代理。
│   │       │   ├── database_session_manager.py     # PostgreSQL 版聊天会话管理器。
│   │       │   ├── mindmap_service.py              # 思维导图生成、保存、更新和导出业务逻辑。
│   │       │   ├── note_service.py                 # 笔记创建、查询、搜索、更新、删除、标签生成、向量同步、导出和关联推荐业务逻辑。
│   │       │   ├── note_template_service.py        # 笔记模板默认初始化、增删改查和排序业务逻辑。
│   │       │   ├── quick_test_service.py           # 快速测试题目生成、答题反馈、会话状态和总结业务逻辑。
│   │       │   ├── review_service.py               # 每日回顾、间隔推进和回顾问题生成业务逻辑。
│   │       │   └── source_collector.py             # 从笔记、知识库或混合来源收集片段，并格式化成 LLM 上下文。
│   │       │
│   │       └── utils/                              # 通用工具层。
│   │           ├── __init__.py                     # utils 包标识文件。
│   │           ├── auth_utils.py                   # 密码哈希、JWT、Token 黑名单、当前用户依赖和用户信息缓存。
│   │           ├── config.py                       # 通用配置常量入口。
│   │           ├── config_handler.py               # YAML 配置加载工具。
│   │           ├── env_loader.py                   # 后端环境加载工具，只读取 config/.env 并解析文件型密钥。
│   │           ├── factory.py                      # 模型工厂，创建阿里云/Ollama 聊天模型、嵌入模型、视觉模型和重排序模型。
│   │           ├── file_handler.py                 # 文档解析工具，支持 PDF、TXT、Word、Markdown、PPT 的异步和同步加载。
│   │           ├── image_extractor.py              # PDF 图片提取、图片目录管理和清理工具。
│   │           ├── magic_compat.py                 # Windows 下 python-magic DLL 路径兼容处理。
│   │           ├── path_tool.py                    # 项目根目录、源码目录、数据目录、媒体目录和配置目录路径工具。
│   │           ├── pdf_multimodal_loader.py        # 多模态 PDF 加载器，结合文本、图片提取和视觉模型生成页面内容。
│   │           ├── prompt_loader.py                # 按类型加载 prompt 文件。
│   │           └── vision_service.py               # 视觉模型服务，处理图片理解、PDF 页面图片描述和模型调用。
│   │
│   └── test/                                       # 后端测试和演示数据夹具。
│       ├── test_demo_dataset.py                    # 演示数据 manifest 的结构和引用完整性测试。
│       ├── test_enterprise_contracts.py            # 企业版关键契约测试，覆盖配置、迁移和主要能力边界。
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
│   ├── vite.config.ts                              # Vite 开发服务器、代理目标和构建配置。
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
│       │   ├── knowledge.ts                        # 知识库列表、上传、详情、切片和删除请求封装。
│       │   ├── mindmaps.ts                         # 思维导图生成、获取、更新和导出请求封装。
│       │   ├── noteTemplates.ts                    # 笔记模板请求封装。
│       │   ├── notes.ts                            # 笔记列表、搜索、CRUD、批量操作、导出和关联请求封装。
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
│       └── views/                                  # 页面组件。
│           ├── AboutView.vue                       # 关于页面。
│           ├── ChatView.vue                        # AI 聊天页面，发起问答并展示消息。
│           ├── KnowledgeView.vue                   # 知识库页面，展示文档、上传文件和查看处理结果。
│           ├── LoginView.vue                       # 登录页面。
│           ├── MindMapView.vue                     # 思维导图页面，选择来源、生成图谱并渲染 Vue Flow。
│           ├── NoteEditorView.vue                  # 笔记编辑页面，创建或编辑标题、正文和分类。
│           ├── NoteListView.vue                    # 笔记列表页面，展示笔记并支持搜索入口。
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
