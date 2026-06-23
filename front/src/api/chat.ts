import { endpoints } from './endpoints'
import client from './client'
import type { ApiResponse, ChatQueryRequest, QuizResponse } from '../types/api'

export const chatApi = {
  queryStream: (body: ChatQueryRequest) => {
    const token = localStorage.getItem('jwt_token')
    return fetch(endpoints.agentQueryStream, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
  },

  generateQuiz: async (data: { selected_files?: string[]; selected_notes?: string[] }) => {
    const res = await client.post<ApiResponse<QuizResponse>>(endpoints.quizGenerate, data, { timeout: 180000 })
    return res.data
  },
}
