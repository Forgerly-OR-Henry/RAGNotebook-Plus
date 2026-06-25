/**
 * 模块职责：前端源码模块，封装 RAGNotebook 客户端的可维护逻辑。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { installDomI18n } from './i18n/dom'
import { useLanguageStore } from './stores/useLanguageStore'
import { useThemeStore } from './stores/useThemeStore'
import './index.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
installDomI18n(useLanguageStore(pinia))
useThemeStore(pinia).initTheme()
app.mount('#app')
