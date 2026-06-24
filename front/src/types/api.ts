/**
 * 模块职责：前端业务 API 封装，负责把视图层调用转换为后端 HTTP 或 SSE 请求。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

/**
 * 接口：`UserInfo` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface UserInfo {
  id?: string
  user_id?: string
  uuid?: string
  username: string
  email: string
  phone?: string
  telephone?: string
  gender?: string | number | null
  bio?: string
  avatar?: string
  date_joined?: string
  is_active?: boolean
}

/**
 * 接口：`LoginResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface LoginResponse {
  token: string
  user: UserInfo
}

/**
 * 接口：`Note` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface Note {
  id: string
  user_id: string
  document_id: string
  title: string
  content: string
  storage_uri?: string | null
  tags: string[] | null
  category: string | null
  folder_id: string | null
  is_pinned: boolean
  created_at: string | null
  updated_at: string | null
}

/**
 * 接口：`NoteFolder` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface NoteFolder {
  id: string
  user_id: string
  name: string
  parent_id: string | null
  note_count: number
  children: NoteFolder[]
  created_at: string | null
  updated_at: string | null
}

/**
 * 接口：`NoteFolderTreeResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface NoteFolderTreeResponse {
  folders: NoteFolder[]
  total_count: number
  unfiled_count: number
}

/**
 * 接口：`NoteListResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface NoteListResponse {
  notes: Note[]
  total_count: number
}

/**
 * 接口：`NoteTemplate` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface NoteTemplate {
  id: string
  user_id: string
  name: string
  icon: string
  category: string
  title: string
  content: string
  tags: string[] | null
  is_default: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

/**
 * 接口：`NoteStats` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface NoteStats {
  total: number
  categories: { category: string; count: number }[]
  uncategorized: number
}

/**
 * 接口：`DeleteCategoryResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface DeleteCategoryResponse {
  deleted_count: number
}

/**
 * 接口：`ChatSession` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ChatSession {
  id: string
  user_id?: string
  project_id?: string | null
  title: string
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
}

/**
 * 接口：`ChatMessage` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ChatMessage {
  id: number
  session_id: string
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, unknown>
  created_at: string
}

/**
 * 接口：`KnowledgeDocument` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeDocument {
  id: string
  document_id?: string
  source_type?: 'knowledge'
  title?: string | null
  user_id?: string
  content_hash?: string
  storage_uri?: string
  file_ext?: string
  filename: string
  original_filename?: string | null
  file_size?: number
  file_type?: string
  mime_type?: string
  category?: string | null
  tags?: string[] | null
  is_pinned: boolean
  status?: string
  status_message?: string | null
  chunk_count: number
  folder_id?: string | null
  preview?: string
  created_at?: string | null
  updated_at?: string | null
}

/**
 * 接口：`KnowledgeChunk` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeChunk {
  chunk_id: string
  index: number
  content: string
  page: number
  images: string[]
}

/**
 * 接口：`KnowledgeDocumentDetail` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeDocumentDetail {
  id: string
  document_id?: string
  source_type?: 'knowledge'
  title?: string | null
  user_id: string
  content_hash?: string
  storage_uri?: string
  file_ext?: string
  filename: string
  original_filename?: string | null
  file_size?: number
  mime_type?: string
  category?: string | null
  tags?: string[] | null
  is_pinned: boolean
  status?: string
  status_message?: string | null
  chunk_count: number
  content: string
  images: string[]
  folder_id?: string | null
  created_at: string | null
  updated_at?: string | null
  chunks: KnowledgeChunk[]
}

/**
 * 接口：`KnowledgeFolder` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeFolder {
  id: string
  user_id: string
  name: string
  parent_id: string | null
  knowledge_count: number
  children: KnowledgeFolder[]
  created_at: string | null
  updated_at: string | null
}

/**
 * 接口：`KnowledgeFolderTreeResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeFolderTreeResponse {
  folders: KnowledgeFolder[]
  total_count: number
  unfiled_count: number
}

/**
 * 接口：`RelatedFragment` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface RelatedFragment {
  id: string
  title: string
  content_preview: string
  content: string
  similarity: number
  source: 'knowledge_base' | 'note'
}

/**
 * 接口：`BatchIdsRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface BatchIdsRequest {
  ids: string[]
}

/**
 * 接口：`BatchCategoryRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface BatchCategoryRequest {
  ids: string[]
  category: string
}

/**
 * 接口：`BatchFolderRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface BatchFolderRequest {
  ids: string[]
  folder_id: string | null
}

/**
 * 接口：`SSEMessage` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface SSEMessage {
  type: 'thinking' | 'response' | 'done' | 'error'
  content?: string
  session_id?: string
  stage?: string
  details?: Record<string, unknown>
}

/**
 * 接口：`KnowledgeUploadProgress` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface KnowledgeUploadProgress {
  event_type: 'start' | 'slicing_completed' | 'writing' | 'completed' | 'error' | 'finish' | string
  filename?: string
  progress?: number
  total_files?: number
  file_index?: number
  step?: string
  message?: string
  success_count?: number
  failed_count?: number
  slice_success_count?: number
  error_message?: string
  chunk_count?: number
  document_id?: string
}

/**
 * 类型：`SourceType` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type SourceType = 'note' | 'knowledge' | 'mixed'
/**
 * 类型：`SourceRefType` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type SourceRefType = 'note' | 'knowledge'
/**
 * 类型：`MindMapSourceType` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type MindMapSourceType = SourceRefType
/**
 * 类型：`Difficulty` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type Difficulty = 'easy' | 'normal' | 'hard'

/**
 * 接口：`ChatSourceRef` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ChatSourceRef {
  source_type: SourceRefType
  source_id: string
}

/**
 * 接口：`ChatQueryRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ChatQueryRequest {
  query: string
  session_id?: string
  project_id?: string
  references?: ChatSourceRef[]
  rag_enabled?: boolean
}

/**
 * 接口：`ChatProject` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ChatProject {
  id: string
  user_id: string
  name: string
  description?: string | null
  source_count: number
  session_count: number
  created_at?: string | null
  updated_at?: string | null
}

/**
 * 接口：`ProjectSource` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ProjectSource {
  id: string
  project_id: string
  source_type: SourceRefType
  source_id: string
  title: string
  preview?: string | null
  status?: string | null
  created_at?: string | null
}

/**
 * 接口：`ProjectListResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ProjectListResponse {
  projects: ChatProject[]
  total_count: number
}

/**
 * 接口：`ProjectSourcesResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface ProjectSourcesResponse {
  sources: ProjectSource[]
  total_count: number
}

/**
 * 接口：`SourceCitation` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface SourceCitation {
  source_type: string
  source_id: string
  title: string
  chunk_id?: string | null
  quote: string
  score?: number | null
}

/**
 * 接口：`QuickTestStartRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestStartRequest {
  source_type: SourceType
  source_ids: string[]
  question_count: number
  difficulty: Difficulty
  focus?: string
}

/**
 * 接口：`QuickTestStartResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestStartResponse {
  session_id: string
  first_question: string
  citations: SourceCitation[]
}

/**
 * 接口：`QuickTestAnswerResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestAnswerResponse {
  feedback: string
  score: number
  next_question?: string | null
  citations: SourceCitation[]
  is_finished: boolean
}

/**
 * 接口：`QuickTestTurn` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestTurn {
  id: string
  turn_index: number
  question: string
  answer?: string | null
  feedback?: string | null
  score?: number | null
  citations: SourceCitation[]
}

/**
 * 接口：`QuickTestSession` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestSession {
  session_id: string
  source_type: string
  source_ids: string[]
  question_count: number
  difficulty: string
  focus?: string | null
  status: string
  current_turn: number
  summary?: string | null
  weak_points: string[]
  recommended_refs: SourceCitation[]
  turns: QuickTestTurn[]
}

/**
 * 接口：`QuickTestFinishResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuickTestFinishResponse {
  final_summary: string
  weak_points: string[]
  recommended_notes: SourceCitation[]
  recommended_documents: SourceCitation[]
}

/**
 * 接口：`QuizQuestion` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuizQuestion {
  id: string
  type: 'single_choice' | 'true_false' | string
  question: string
  options: string[]
  answer: string
  explanation?: string | null
}

/**
 * 接口：`QuizResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface QuizResponse {
  title: string
  description?: string | null
  questions: QuizQuestion[]
}

/**
 * 接口：`MindMapNode` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface MindMapNode {
  id: string
  label: string
  level: number
  type: string
  summary?: string | null
  source_refs: string[]
}

/**
 * 接口：`MindMapEdge` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface MindMapEdge {
  id: string
  source: string
  target: string
  label?: string | null
}

/**
 * 接口：`MindMapGenerateRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface MindMapGenerateRequest {
  source_type: MindMapSourceType
  source_ids: string[]
  max_nodes: number
  max_depth: number
  focus?: string
}

/**
 * 接口：`MindMapResponse` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export interface MindMapResponse {
  mindmap_id: string
  title: string
  source_type: string
  source_ids: string[]
  nodes: MindMapNode[]
  edges: MindMapEdge[]
  citations: SourceCitation[]
  source_refs: Record<string, unknown>[]
  version: number
}
