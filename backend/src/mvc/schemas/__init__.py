"""
模块职责：Pydantic schema 模块，负责声明接口请求、响应和嵌套数据结构。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.schemas.chat import (
    AgentResponse,
    AgentStep,
    QueryRequest,
    QuizGenerateRequest,
    QuizQuestion,
    QuizResponse,
    RAGRequest,
    RAGResponse,
    ReorderRequest,
    ReorderResponse,
    SessionResponse,
)
from mvc.schemas.knowledge import (
    ChunkDetail,
    ChunkInfo,
    DocumentChunksResponse,
    DocumentDetailResponse,
    DocumentResponse,
    KnowledgeBatchCategoryRequest,
    KnowledgeBatchFolderRequest,
    KnowledgeDocumentMetadataUpdate,
    KnowledgeFolderCreate,
    KnowledgeFolderResponse,
    KnowledgeFolderTreeResponse,
    KnowledgeFolderUpdate,
    KnowledgeListResponse,
)
from mvc.schemas.mindmaps import MindMapEdge, MindMapGenerateRequest, MindMapNode, MindMapResponse, MindMapUpdateRequest
from mvc.schemas.note_templates import NoteTemplateCreate, NoteTemplateReorder, NoteTemplateResponse, NoteTemplateUpdate
from mvc.schemas.notes import BatchCategoryRequest, BatchFolderRequest, BatchIdsRequest, BatchPinRequest, NoteCreate, NoteFolderCreate, NoteFolderResponse, NoteFolderTreeResponse, NoteFolderUpdate, NoteListResponse, NoteResponse, NoteSearchRequest, NoteUpdate, PageRequest, RelatedNoteItem, RelatedNotesResponse
from mvc.schemas.projects import ProjectCreateRequest, ProjectListResponse, ProjectResponse, ProjectSourceResponse, ProjectSourcesAddRequest, ProjectSourcesResponse, ProjectUpdateRequest
from mvc.schemas.quick_tests import QuickTestAnswerRequest, QuickTestAnswerResponse, QuickTestCreateRequest, QuickTestFinishResponse, QuickTestSessionResponse, QuickTestStartResponse, QuickTestTurnResponse
from mvc.schemas.sources import Difficulty, SourceCitation, SourceReference, SourceRefType, SourceType
from mvc.schemas.users import ActionResponse, LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, ResetPasswordRequest, TokenRefreshRequest, UserDetailResponse, UserResponse, UserUpdateRequest
