/**
 * 模块职责：Pinia 状态模块，负责管理跨页面共享的客户端状态。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { defineStore } from 'pinia'

/**
 * 类型：`Lang` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type Lang = 'zh-CN' | 'en-US'

export const useLanguageStore = defineStore('language', {
  state: () => ({
    lang: ((localStorage.getItem('language') as Lang) || 'zh-CN') as Lang,
  }),
  actions: {
    setLang(lang: Lang) {
      this.lang = lang
      localStorage.setItem('language', lang)
    },
  },
})
