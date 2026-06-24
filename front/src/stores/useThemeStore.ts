/**
 * 模块职责：Pinia 状态模块，负责管理跨页面共享的客户端状态。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { defineStore } from 'pinia'

/**
 * 类型：`Theme` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type Theme = 'light' | 'dark'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: (localStorage.getItem('theme') as Theme) || 'light',
  }),
  actions: {
    initTheme() {
      const localTheme = localStorage.getItem('theme') as Theme | null
      if (localTheme === 'dark' || localTheme === 'light') {
        this.setTheme(localTheme)
        return
      }

      const mediaTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      this.setTheme(mediaTheme)
    },
    toggleTheme() {
      this.setTheme(this.theme === 'light' ? 'dark' : 'light')
    },
    setTheme(theme: Theme) {
      if (theme !== 'dark' && theme !== 'light') {
        return
      }

      this.theme = theme
      localStorage.setItem('theme', theme)
      if (theme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    },
  },
})
