/**
 * 模块职责：前端业务 API 封装，负责把视图层调用转换为后端 HTTP 或 SSE 请求。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import client from '../../api/client'
import { endpoints } from '../../api/endpoints'
import type { ApiResponse, DeleteCategoryResponse, Note, NoteFolder, NoteFolderTreeResponse, NoteListResponse, NoteStats, RelatedFragment } from '../../types/api'

export const notesApi = {
  list: async (params: { page?: number; page_size?: number; category?: string; tag?: string; folder_id?: string; unfiled?: boolean; sort_by?: string }) => {
    const res = await client.get<ApiResponse<NoteListResponse>>(endpoints.noteList, { params })
    return res.data
  },

  get: async (id: string) => {
    const res = await client.get<ApiResponse<Note>>(endpoints.noteDetail(id))
    return res.data
  },

  create: async (data: { title: string; content: string; category?: string; tags?: string[]; folder_id?: string | null }) => {
    const res = await client.post<ApiResponse<Note>>(endpoints.noteCreate, data)
    return res.data
  },

  importFile: async (file: File, category?: string, folderId?: string | null) => {
    const formData = new FormData()
    formData.append('file', file)
    if (category) {
      formData.append('category', category)
    }
    if (folderId) {
      formData.append('folder_id', folderId)
    }

    const res = await client.post<ApiResponse<Note>>(endpoints.noteImport, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  update: async (id: string, data: Partial<Note>) => {
    const res = await client.put<ApiResponse<Note>>(endpoints.noteUpdate(id), data)
    return res.data
  },

  delete: async (id: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.noteDelete(id))
    return res.data
  },

  stats: async () => {
    const res = await client.get<ApiResponse<NoteStats>>(endpoints.noteStats)
    return res.data
  },

  search: async (query: string, limit = 30, filters: { folder_id?: string; unfiled?: boolean } = {}) => {
    const res = await client.get<ApiResponse<NoteListResponse>>(endpoints.noteSearch, { params: { q: query, limit, ...filters } })
    return res.data
  },

  listFolders: async () => {
    const res = await client.get<ApiResponse<NoteFolderTreeResponse>>(endpoints.noteFolders)
    return res.data
  },

  createFolder: async (data: { name: string; parent_id?: string | null }) => {
    const res = await client.post<ApiResponse<NoteFolder>>(endpoints.noteFolders, data)
    return res.data
  },

  updateFolder: async (id: string, data: { name?: string; parent_id?: string | null }) => {
    const res = await client.put<ApiResponse<NoteFolder>>(endpoints.noteFolder(id), data)
    return res.data
  },

  deleteFolder: async (id: string, mode: 'unfile' | 'delete_notes') => {
    const res = await client.delete<ApiResponse<null>>(endpoints.noteFolder(id), { params: { mode } })
    return res.data
  },

  related: async (id: string) => {
    const res = await client.get<ApiResponse<RelatedFragment[]>>(endpoints.noteRelated(id))
    return res.data
  },

  download: async (id: string) => {
    const res = await client.get<Blob>(endpoints.noteDownload(id), { responseType: 'blob' })
    return res.data
  },

  autocomplete: async (context: string) => {
    const res = await client.post<ApiResponse<{ completion: string }>>(endpoints.noteAutocomplete, { context })
    return res.data
  },

  autoTag: async (id: string) => {
    const res = await client.post<ApiResponse<Note>>(endpoints.noteAutoTag(id))
    return res.data
  },

  batchDelete: async (ids: string[]) => {
    const res = await client.post<ApiResponse<null>>(endpoints.noteBatchDelete, { ids })
    return res.data
  },

  batchDownload: async (ids: string[]) => {
    const res = await client.post<Blob>(endpoints.noteBatchDownload, { ids }, { responseType: 'blob' })
    return res.data
  },

  batchUpdateCategory: async (ids: string[], category: string) => {
    const res = await client.put<ApiResponse<null>>(endpoints.noteBatchCategory, { ids, category })
    return res.data
  },

  batchUpdateFolder: async (ids: string[], folder_id: string | null) => {
    const res = await client.put<ApiResponse<null>>(endpoints.noteBatchFolder, { ids, folder_id })
    return res.data
  },

  batchPin: async (ids: string[], is_pinned: boolean) => {
    const res = await client.put<ApiResponse<null>>(endpoints.noteBatchPin, { ids, is_pinned })
    return res.data
  },

  deleteCategory: async (category: string) => {
    const res = await client.delete<ApiResponse<DeleteCategoryResponse>>(endpoints.noteCategoryDelete(category))
    return res.data
  },

  pin: async (id: string) => {
    const res = await client.put<ApiResponse<Note>>(endpoints.notePin(id))
    return res.data
  },
}
