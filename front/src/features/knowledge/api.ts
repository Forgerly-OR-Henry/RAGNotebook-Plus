import client from '../../api/client'
import { endpoints } from '../../api/endpoints'
import { uploadFormSse, type StreamResult } from '../../api/stream'
import type {
  ApiResponse,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeFolder,
  KnowledgeFolderTreeResponse,
  KnowledgeUploadProgress,
  NoteStats,
  DeleteCategoryResponse,
} from '../../types/api'

interface KnowledgeListData {
  documents: KnowledgeDocument[]
  total_count: number
}

type KnowledgeUploadResult = StreamResult<KnowledgeUploadProgress>

async function uploadWithProgress(
  files: File[],
  onProgress?: (event: KnowledgeUploadProgress) => void,
  folderId?: string | null,
  category?: string | null,
): Promise<KnowledgeUploadResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  if (folderId) {
    formData.append('folder_id', folderId)
  }
  if (category) {
    formData.append('category', category)
  }

  return uploadFormSse(endpoints.knowledgeDocuments, formData, onProgress)
}

export const knowledgeApi = {
  list: async (params: { folder_id?: string; unfiled?: boolean; category?: string } = {}) => {
    const res = await client.get<ApiResponse<KnowledgeListData>>(endpoints.knowledgeDocuments, { params })
    return res.data
  },

  uploadSingle: async (file: File, folderId?: string | null, category?: string | null) => uploadWithProgress([file], undefined, folderId, category),

  uploadMultiple: async (files: File[], folderId?: string | null, category?: string | null) => uploadWithProgress(files, undefined, folderId, category),

  uploadStream: uploadWithProgress,

  detail: async (documentId: string) => {
    const res = await client.get<ApiResponse<KnowledgeDocumentDetail>>(endpoints.knowledgeDocument(documentId))
    return res.data
  },

  updateMetadata: async (documentId: string, payload: { category?: string | null; tags?: string[] | null }) => {
    const res = await client.put<ApiResponse<KnowledgeDocument>>(endpoints.knowledgeDocumentMetadata(documentId), payload)
    return res.data
  },

  autoTag: async (documentId: string) => {
    const res = await client.post<ApiResponse<KnowledgeDocument>>(endpoints.knowledgeDocumentAutoTag(documentId))
    return res.data
  },

  fileBlob: async (documentId: string) => {
    return client.get<Blob>(endpoints.knowledgeDocumentFile(documentId), { responseType: 'blob' })
  },

  chunks: async (documentId: string) => {
    const res = await client.get<ApiResponse<unknown[]>>(endpoints.knowledgeDocumentChunks(documentId))
    return res.data
  },

  delete: async (documentId: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeDocument(documentId))
    return res.data
  },

  cleanAll: async () => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeDocuments)
    return res.data
  },

  listFolders: async () => {
    const res = await client.get<ApiResponse<KnowledgeFolderTreeResponse>>(endpoints.knowledgeFolders)
    return res.data
  },

  createFolder: async (payload: { name: string; parent_id?: string | null }) => {
    const res = await client.post<ApiResponse<KnowledgeFolder>>(endpoints.knowledgeFolders, payload)
    return res.data
  },

  updateFolder: async (folderId: string, payload: { name?: string; parent_id?: string | null }) => {
    const res = await client.put<ApiResponse<KnowledgeFolder>>(endpoints.knowledgeFolder(folderId), payload)
    return res.data
  },

  deleteFolder: async (folderId: string, mode: 'unfile' | 'delete_documents') => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeFolder(folderId), { params: { mode } })
    return res.data
  },

  batchUpdateFolder: async (ids: string[], folderId: string | null) => {
    const res = await client.put<ApiResponse<null>>(endpoints.knowledgeBatchFolder, { ids, folder_id: folderId })
    return res.data
  },

  batchUpdateCategory: async (ids: string[], category: string | null) => {
    const res = await client.put<ApiResponse<null>>(endpoints.knowledgeBatchCategory, { ids, category })
    return res.data
  },

  stats: async () => {
    const res = await client.get<ApiResponse<NoteStats>>(endpoints.knowledgeStats)
    return res.data
  },

  deleteCategory: async (category: string) => {
    const res = await client.delete<ApiResponse<DeleteCategoryResponse>>(endpoints.knowledgeCategoryDelete(category))
    return res.data
  },
}
