import client from './client'
import { endpoints } from './endpoints'
import type { ApiResponse, MindMapGenerateRequest, MindMapResponse } from '../types/api'

export const mindmapApi = {
  generate: async (data: MindMapGenerateRequest) => {
    const res = await client.post<ApiResponse<MindMapResponse>>(endpoints.mindmapGenerate, data, { timeout: 180000 })
    return res.data.data
  },
  get: async (id: string) => {
    const res = await client.get<ApiResponse<MindMapResponse>>(endpoints.mindmapDetail(id))
    return res.data.data
  },
  update: async (data: MindMapResponse) => {
    const res = await client.put<ApiResponse<MindMapResponse>>(endpoints.mindmapUpdate(data.mindmap_id), {
      title: data.title,
      nodes: data.nodes,
      edges: data.edges,
    })
    return res.data.data
  },
  export: async (id: string, format: 'json' | 'mermaid') => {
    const res = await client.get<ApiResponse<{ format: string; content: unknown }>>(endpoints.mindmapExport(id), {
      params: { format },
    })
    return res.data.data
  },
}
