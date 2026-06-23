import client from './client'
import { endpoints } from './endpoints'
import type { ApiResponse, ChatSession } from '../types/api'

interface SessionsData {
  sessions: ChatSession[]
}

interface SessionDetailData {
  session_id: string
  history: [string, string][]
}

export const sessionsApi = {
  list: async (userId: string, projectId?: string | null) => {
    const res = await client.get<ApiResponse<SessionsData>>(endpoints.getUserSessions(userId), {
      params: projectId ? { project_id: projectId } : undefined,
    })
    return res.data
  },

  get: async (id: string) => {
    const res = await client.get<ApiResponse<SessionDetailData>>(endpoints.getSession(id))
    return res.data
  },

  delete: async (id: string) => {
    const res = await client.delete<ApiResponse<null>>(endpoints.deleteSession(id))
    return res.data
  },
}
