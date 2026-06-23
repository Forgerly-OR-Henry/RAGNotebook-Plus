import { defineStore } from 'pinia'

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
