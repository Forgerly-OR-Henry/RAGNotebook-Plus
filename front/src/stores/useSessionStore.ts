/**
 * 模块职责：Pinia 状态模块，负责管理跨页面共享的客户端状态。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { defineStore } from 'pinia'
import type { ChatSession } from '../types/api'

export const useSessionStore = defineStore('sessions', {
  state: () => ({
    sessions: [] as ChatSession[],
    currentSession: null as ChatSession | null,
    loading: false,
  }),
  actions: {
    setSessions(sessions: ChatSession[]) {
      this.sessions = sessions
    },
    setCurrentSession(session: ChatSession | null) {
      this.currentSession = session
    },
    addSession(session: ChatSession) {
      this.sessions = [session, ...this.sessions]
    },
    removeSession(id: string) {
      this.sessions = this.sessions.filter((session) => session.id !== id)
      if (this.currentSession?.id === id) this.currentSession = null
    },
    setLoading(loading: boolean) {
      this.loading = loading
    },
    clearSessions() {
      this.sessions = []
      this.currentSession = null
    },
  },
})
