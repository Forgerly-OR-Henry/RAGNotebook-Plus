/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import client from './client'
import { endpoints } from './endpoints'
import type { ApiResponse, ChatSession } from '../types/api'

/**
 * 接口：`SessionsData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface SessionsData {
  sessions: ChatSession[]
}

/**
 * 接口：`SessionDetailData` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
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
