/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import client from './client'
import { endpoints } from './endpoints'
import type {
  ApiResponse,
  QuickTestAnswerResponse,
  QuickTestFinishResponse,
  QuickTestSession,
  QuickTestStartRequest,
  QuickTestStartResponse,
} from '../types/api'

export const quickTestApi = {
  create: async (data: QuickTestStartRequest) => {
    const res = await client.post<ApiResponse<QuickTestStartResponse>>(endpoints.quickTestCreate, data)
    return res.data.data
  },
  answer: async (sessionId: string, answer: string) => {
    const res = await client.post<ApiResponse<QuickTestAnswerResponse>>(endpoints.quickTestAnswer(sessionId), { answer })
    return res.data.data
  },
  detail: async (sessionId: string) => {
    const res = await client.get<ApiResponse<QuickTestSession>>(endpoints.quickTestDetail(sessionId))
    return res.data.data
  },
  finish: async (sessionId: string) => {
    const res = await client.post<ApiResponse<QuickTestFinishResponse>>(endpoints.quickTestFinish(sessionId))
    return res.data.data
  },
}
