import client from '../../api/client'
import { endpoints } from '../../api/endpoints'
import type { ApiResponse, KnowledgeDocument, KnowledgeDocumentDetail, KnowledgeUploadProgress } from '../../types/api'

interface KnowledgeListData {
  documents: KnowledgeDocument[]
  total_count: number
}

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

  if (!data) {
    return null
  }

  return JSON.parse(data) as KnowledgeUploadProgress
}

async function readErrorResponse(response: Response) {
  const text = await response.text()
  if (!text) {
    return `上传失败：${response.status}`
  }
  try {
    const data = JSON.parse(text) as { detail?: unknown; message?: string }
    if (typeof data.detail === 'string') {
      return data.detail
    }
    return data.message || text
  } catch {
    return text
  }
}

async function uploadWithProgress(files: File[], onProgress?: (event: KnowledgeUploadProgress) => void): Promise<KnowledgeUploadResult> {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  const headers = new Headers()
  const token = localStorage.getItem(JWT_KEY)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(endpoints.knowledgeDocuments, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (response.status === 401) {
    localStorage.removeItem(JWT_KEY)
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }

  if (!response.ok) {
    throw new Error(await readErrorResponse(response))
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('浏览器无法读取上传进度流')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  const result: KnowledgeUploadResult = {
    finalEvent: null,
    lastError: '',
  }

  const consumeBuffer = (flush = false) => {
    const parts = buffer.split(/\r?\n\r?\n/)
    buffer = flush ? '' : parts.pop() || ''

    for (const block of parts) {
      const event = parseSseBlock(block)
      if (!event) {
        continue
      }
      result.finalEvent = event
      if (event.event_type === 'error') {
        result.lastError = event.error_message || event.message || result.lastError
      }
      onProgress?.(event)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    consumeBuffer()
  }

  buffer += decoder.decode()
  consumeBuffer(true)

  if (!result.finalEvent) {
    throw new Error('上传进度流中断，请重试')
  }

  if (result.finalEvent.event_type !== 'finish') {
    throw new Error(result.lastError || result.finalEvent.message || '上传处理未完成，请重试')
  }

  return result
}

export const knowledgeApi = {
  list: async () => {
    const res = await client.get<ApiResponse<KnowledgeListData>>(endpoints.knowledgeDocuments)
    return res.data
  },

  uploadSingle: async (file: File) => uploadWithProgress([file]),

  uploadMultiple: async (files: File[]) => uploadWithProgress(files),

  uploadStream: uploadWithProgress,

  detail: async (documentId: string) => {
    const res = await client.get<ApiResponse<KnowledgeDocumentDetail>>(endpoints.knowledgeDocument(documentId))
    return res.data
  },

  chunks: async (documentId: string) => {
    const res = await client.get<ApiResponse<unknown[]>>(endpoints.knowledgeDocumentChunks(documentId))
    return res.data
  },

  delete: async (documentId: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeDocument(documentId))
    return res.data
  },

  deleteByFilename: async (filename: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeDeleteFilename, { params: { filename } })
    return res.data
  },

  deleteByMd5: async (md5: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeMd5Delete(md5))
    return res.data
  },

  cleanAll: async () => {
    const res = await client.delete<ApiResponse<null>>(endpoints.knowledgeDocuments)
    return res.data
  },
}
