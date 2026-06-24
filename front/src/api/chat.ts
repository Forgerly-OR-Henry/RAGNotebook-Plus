/**
 * 模块职责：前端 API 模块，负责封装 HTTP/SSE 请求并保持视图层调用简洁。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { endpoints } from './endpoints'
import client from './client'
import { postJsonStream } from './stream'
import type { ApiResponse, ChatQueryRequest, QuizResponse } from '../types/api'

export const chatApi = {
  queryStream: (body: ChatQueryRequest) => postJsonStream(endpoints.agentQueryStream, body),

  generateQuiz: async (data: { selected_files?: string[]; selected_notes?: string[] }) => {
    const res = await client.post<ApiResponse<QuizResponse>>(endpoints.quizGenerate, data, { timeout: 180000 })
    return res.data
  },
}
