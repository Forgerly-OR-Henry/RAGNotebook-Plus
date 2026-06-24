/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import client from './client'
import { endpoints } from './endpoints'
import { uploadFormSse, type StreamResult } from './stream'
import type {
  ApiResponse,
  ChatProject,
  ChatSourceRef,
  KnowledgeUploadProgress,
  Note,
  ProjectListResponse,
  ProjectSourcesResponse,
} from '../types/api'

/**
 * 类型：`KnowledgeUploadResult` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type KnowledgeUploadResult = StreamResult<KnowledgeUploadProgress>

/**
 * 用途：执行uploadProjectKnowledge相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function uploadProjectKnowledge(
  projectId: string,
  files: File[],
  onProgress?: (event: KnowledgeUploadProgress) => void,
): Promise<KnowledgeUploadResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  return uploadFormSse(endpoints.projectKnowledgeDocuments(projectId), formData, onProgress)
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
