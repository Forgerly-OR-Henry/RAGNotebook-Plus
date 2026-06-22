export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface UserInfo {
  id?: string
  user_id?: string
  uuid?: string
  username: string
  email: string
  phone?: string
  gender?: string
  bio?: string
  avatar?: string
  date_joined?: string
  is_active?: boolean
}

export interface LoginResponse {
  token: string
  user: UserInfo
}

export interface Note {
  id: string
  user_id: string
  title: string
  content: string
  tags: string[]
  category: string
  is_pinned: boolean
  created_at: string
  updated_at: string
}

export interface NoteListResponse {
  notes: Note[]
  total_count: number
}

export interface NoteTemplate {
  id: string
  user_id: string
  name: string
  icon: string
  category: string
  title: string
  content: string
  tags: string[]
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface NoteStats {
  total: number
  categories: { category: string; count: number }[]
  uncategorized: number
}

export interface DeleteCategoryResponse {
  deleted_count: number
}

export interface ChatSession {
  id: string
  user_id?: string
  title: string
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  session_id: string
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, unknown>
  created_at: string
}

export interface KnowledgeDocument {
  id: string
  document_id?: string
  user_id?: string
  md5?: string
  filename: string
  original_filename?: string | null
  file_size?: number
  file_type?: string
  mime_type?: string
  status?: string
  status_message?: string | null
  chunk_count: number
  preview?: string
  created_at: string
  updated_at?: string | null
}

export interface KnowledgeChunk {
  chunk_id: string
  index: number
  content: string
  page: number
  images: string[]
}

export interface KnowledgeDocumentDetail {
  id: string
  document_id?: string
  user_id: string
  md5: string
  filename: string
  original_filename?: string | null
  file_size?: number
  mime_type?: string
  status?: string
  status_message?: string | null
  chunk_count: number
  content: string
  images: string[]
  created_at: string | null
  updated_at?: string | null
  chunks: KnowledgeChunk[]
}

export interface RelatedFragment {
  id: string
  title: string
  content_preview: string
  content: string
  similarity: number
  source: 'knowledge_base' | 'note'
}

export interface BatchIdsRequest {
  ids: string[]
}

export interface BatchCategoryRequest {
  ids: string[]
  category: string
}

export interface ReviewItem {
  review_id: string
  note_id: string
  title: string
  content_preview: string
  tags: string[]
  category: string
  review_count: number
  last_reviewed_at: string | null
  interval_days: number
}

export interface ReviewQuestion {
  question: string
  choices: string[]
  answer: string
}

export interface ReviewListData {
  reviews: ReviewItem[]
  total_count: number
}

export interface SSEMessage {
  type: 'thinking' | 'response' | 'done' | 'error'
  content?: string
  session_id?: string
  stage?: string
  details?: Record<string, unknown>
}

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
}

export type SourceType = 'note' | 'knowledge' | 'mixed'
export type Difficulty = 'easy' | 'normal' | 'hard'

export interface SourceCitation {
  source_type: string
  source_id: string
  title: string
  chunk_id?: string | null
  quote: string
  score?: number | null
}

export interface QuickTestStartRequest {
  source_type: SourceType
  source_ids: string[]
  question_count: number
  difficulty: Difficulty
  focus?: string
}

export interface QuickTestStartResponse {
  session_id: string
  first_question: string
  citations: SourceCitation[]
}

export interface QuickTestAnswerResponse {
  feedback: string
  score: number
  next_question?: string | null
  citations: SourceCitation[]
  is_finished: boolean
}

export interface QuickTestTurn {
  id: string
  turn_index: number
  question: string
  answer?: string | null
  feedback?: string | null
  score?: number | null
  citations: SourceCitation[]
}

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

export interface QuickTestFinishResponse {
  final_summary: string
  weak_points: string[]
  recommended_notes: SourceCitation[]
  recommended_documents: SourceCitation[]
}

export interface MindMapNode {
  id: string
  label: string
  level: number
  type: string
  summary?: string | null
  source_refs: string[]
}

export interface MindMapEdge {
  id: string
  source: string
  target: string
  label?: string | null
}

export interface MindMapGenerateRequest {
  source_type: SourceType
  source_ids: string[]
  max_nodes: number
  max_depth: number
  focus?: string
}

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
