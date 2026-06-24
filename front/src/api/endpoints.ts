/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export const endpoints = {
  // Auth
  login: '/user/login/',
  logout: '/user/logout/',
  register: '/user/register/',
  profile: '/user/detail/',
  userUpdate: '/user/update/',
  changePassword: '/user/reset-password/',

  // Health
  healthReady: '/health/ready',

  // File upload
  uploadFile: '/file/upload/',

  // AI Chat
  agentQueryStream: '/chat/agent/query/stream',
  ragQuery: '/chat/rag/query',
  quizGenerate: '/chat/quiz/generate',

  // Chat Projects
  projects: '/projects',
  project: (id: string) => `/projects/${id}`,
  projectSources: (id: string) => `/projects/${id}/sources`,
  projectSource: (projectId: string, sourceType: string, sourceId: string) => `/projects/${projectId}/sources/${sourceType}/${sourceId}`,
  projectKnowledgeDocuments: (id: string) => `/projects/${id}/knowledge/documents`,
  projectNoteImport: (id: string) => `/projects/${id}/notes/import`,

  // Sessions
  getSession: (id: string) => `/chat/session/${id}`,
  deleteSession: (id: string) => `/chat/session/${id}`,
  getAllSessions: '/chat/sessions',
  getUserSessions: (userId: string) => `/chat/sessions/${userId}`,

  // Knowledge Base
  knowledgeDocuments: '/knowledge/documents',
  knowledgeDocument: (id: string) => `/knowledge/documents/${id}`,
  knowledgeDocumentMetadata: (id: string) => `/knowledge/documents/${id}/metadata`,
  knowledgeDocumentAutoTag: (id: string) => `/knowledge/documents/${id}/auto-tag`,
  knowledgeDocumentPin: (id: string) => `/knowledge/documents/${id}/pin`,
  knowledgeDocumentFile: (id: string) => `/knowledge/documents/${id}/file`,
  knowledgeDocumentPreview: (id: string) => `/knowledge/documents/${id}/preview`,
  knowledgeDocumentChunks: (id: string) => `/knowledge/documents/${id}/chunks`,
  documentDownload: (id: string) => `/documents/${id}/download`,
  uploadSingleFile: '/knowledge/documents',
  uploadMultipleFiles: '/knowledge/documents',
  uploadMultipleStream: '/knowledge/documents',
  cleanVectors: '/knowledge/documents',
  knowledgeList: '/knowledge/documents',
  knowledgeDetail: (id: string) => `/knowledge/documents/${id}`,
  knowledgeChunks: (id: string) => `/knowledge/documents/${id}/chunks`,
  knowledgeFolders: '/knowledge/folders',
  knowledgeFolder: (id: string) => `/knowledge/folders/${id}`,
  knowledgeBatchFolder: '/knowledge/batch/folder',
  knowledgeBatchCategory: '/knowledge/batch/category',
  knowledgeStats: '/knowledge/stats',
  knowledgeCategoryDelete: (category: string) => `/knowledge/category/${encodeURIComponent(category)}`,

  // Documents reorder
  reorderDocuments: '/chat/reorder',

  // Notes
  noteCreate: '/note/create',
  noteImport: '/note/import',
  noteUpdate: (id: string) => `/note/${id}`,
  noteDelete: (id: string) => `/note/${id}`,
  noteDetail: (id: string) => `/note/${id}`,
  noteList: '/note/list',
  noteSearch: '/note/search',
  noteAutoTag: (id: string) => `/note/${id}/auto-tag`,
  noteRelated: (id: string) => `/note/${id}/related`,
  noteDownload: (id: string) => `/note/${id}/download`,
  notePin: (id: string) => `/note/${id}/pin`,
  noteAutocomplete: '/note/autocomplete',
  noteStats: '/note/stats',
  noteFolders: '/note/folders',
  noteFolder: (id: string) => `/note/folders/${id}`,
  noteAssistStream: '/note/assist/stream',

  // Batch operations
  noteBatchDelete: '/note/batch/delete',
  noteBatchDownload: '/note/batch/download',
  noteBatchCategory: '/note/batch/category',
  noteBatchFolder: '/note/batch/folder',
  noteBatchPin: '/note/batch/pin',
  noteCategoryDelete: (category: string) => `/note/category/${encodeURIComponent(category)}`,

  // Quick Test
  quickTestCreate: '/quick-test/sessions',
  quickTestAnswer: (id: string) => `/quick-test/sessions/${id}/answer`,
  quickTestDetail: (id: string) => `/quick-test/sessions/${id}`,
  quickTestFinish: (id: string) => `/quick-test/sessions/${id}/finish`,

  // Mind maps
  mindmapGenerate: '/mindmaps/generate',
  mindmapDetail: (id: string) => `/mindmaps/${id}`,
  mindmapUpdate: (id: string) => `/mindmaps/${id}`,
  mindmapExport: (id: string) => `/mindmaps/${id}/export`,

  // Note Templates
  noteTemplateList: '/note-template/list',
  noteTemplateCreate: '/note-template/create',
  noteTemplateUpdate: (id: string) => `/note-template/${id}`,
  noteTemplateDelete: (id: string) => `/note-template/${id}`,
  noteTemplateReorder: '/note-template/reorder',
} as const
