/**
 * 模块职责：Pinia 状态模块，负责管理跨页面共享的客户端状态。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { defineStore } from 'pinia'
import { DEFAULT_LANG, normalizeLang, type Lang } from '../i18n/messages'

/**
 * 类型：`Lang` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
const LANGUAGE_KEY = 'language'

function applyDocumentLang(lang: Lang) {
  if (typeof document === 'undefined') return
  document.documentElement.lang = lang
}

export const useLanguageStore = defineStore('language', {
  state: () => ({
    lang: normalizeLang(typeof localStorage === 'undefined' ? DEFAULT_LANG : localStorage.getItem(LANGUAGE_KEY)),
  }),
  actions: {
    initLanguage() {
      applyDocumentLang(this.lang)
    },
    setLang(lang: Lang) {
      const normalized = normalizeLang(lang)
      this.lang = normalized
      localStorage.setItem(LANGUAGE_KEY, normalized)
      applyDocumentLang(normalized)
    },
  },
})
