import client from './client'
import { endpoints } from './endpoints'
import type {
  ApiResponse,
  ChatProject,
  ChatSourceRef,
  KnowledgeUploadProgress,
  Note,
  ProjectListResponse,
  ProjectSourcesResponse,
} from '../types/api'

interface KnowledgeUploadResult {
  finalEvent: KnowledgeUploadProgress | null
  lastError: string
}

const JWT_KEY = 'jwt_token'

function parseSseBlock(block: string): KnowledgeUploadProgress | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
    .trim()

  return data ? JSON.parse(data) as KnowledgeUploadProgress : null
}

async function readErrorResponse(response: Response) {
  const text = await response.text()
  if (!text) return `上传失败：${response.status}`
  try {
    const data = JSON.parse(text) as { detail?: unknown; message?: string }
    return typeof data.detail === 'string' ? data.detail : data.message || text
  } catch {
    return text
  }
}

async function uploadProjectKnowledge(
  projectId: string,
  files: File[],
  onProgress?: (event: KnowledgeUploadProgress) => void,
): Promise<KnowledgeUploadResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  const headers = new Headers()
  const token = localStorage.getItem(JWT_KEY)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(endpoints.projectKnowledgeDocuments(projectId), {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401) {
    localStorage.removeItem(JWT_KEY)
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }
  if (!response.ok) throw new Error(await readErrorResponse(response))

  const reader = response.body?.getReader()
  if (!reader) throw new Error('浏览器无法读取上传进度流')

  const decoder = new TextDecoder()
  let buffer = ''
  const result: KnowledgeUploadResult = { finalEvent: null, lastError: '' }

  const consumeBuffer = (flush = false) => {
    const parts = buffer.split(/\r?\n\r?\n/)
    buffer = flush ? '' : parts.pop() || ''
    for (const block of parts) {
      const event = parseSseBlock(block)
      if (!event) continue
      result.finalEvent = event
      if (event.event_type === 'error') result.lastError = event.error_message || event.message || result.lastError
      onProgress?.(event)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    consumeBuffer()
  }
  buffer += decoder.decode()
  consumeBuffer(true)

  if (!result.finalEvent) throw new Error('上传进度流中断，请重试')
  if (result.finalEvent.event_type !== 'finish') {
    throw new Error(result.lastError || result.finalEvent.message || '上传处理未完成，请重试')
  }
  return result
}

export const projectsApi = {
  list: async () => {
    const res = await client.get<ApiResponse<ProjectListResponse>>(endpoints.projects)
    return res.data
  },

  create: async (data: { name: string; description?: string }) => {
    const res = await client.post<ApiResponse<ChatProject>>(endpoints.projects, data)
    return res.data
  },

  update: async (id: string, data: { name?: string; description?: string | null }) => {
    const res = await client.patch<ApiResponse<ChatProject>>(endpoints.project(id), data)
    return res.data
  },

  delete: async (id: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.project(id))
    return res.data
  },

  sources: async (projectId: string) => {
    const res = await client.get<ApiResponse<ProjectSourcesResponse>>(endpoints.projectSources(projectId))
    return res.data
  },

  addSources: async (projectId: string, sources: ChatSourceRef[]) => {
    const res = await client.post<ApiResponse<ProjectSourcesResponse>>(endpoints.projectSources(projectId), { sources })
    return res.data
  },

  removeSource: async (projectId: string, source: ChatSourceRef) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.projectSource(projectId, source.source_type, source.source_id))
    return res.data
  },

  uploadKnowledge: uploadProjectKnowledge,

  importNote: async (projectId: string, file: File, category?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (category) formData.append('category', category)
    const res = await client.post<ApiResponse<{ note: Note; sources: ProjectSourcesResponse['sources'] }>>(
      endpoints.projectNoteImport(projectId),
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    return res.data
  },
}
