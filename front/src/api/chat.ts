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
