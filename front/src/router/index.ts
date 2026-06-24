/**
 * 模块职责：Vue Router 配置模块，负责页面路由、认证跳转和视图挂载。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { getJwtToken } from '../api/authToken'
import AppShell from '../components/AppShell.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'

/**
 * 用途：执行NoteListView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const NoteListView = () => import('../views/NoteListView.vue')
/**
 * 用途：执行NoteEditorView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const NoteEditorView = () => import('../views/NoteEditorView.vue')
/**
 * 用途：执行ChatView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const ChatView = () => import('../views/ChatView.vue')
/**
 * 用途：执行KnowledgeView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const KnowledgeView = () => import('../views/KnowledgeView.vue')
/**
 * 用途：执行KnowledgeDetailView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const KnowledgeDetailView = () => import('../views/KnowledgeDetailView.vue')
/**
 * 用途：执行QuickTestView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const QuickTestView = () => import('../views/QuickTestView.vue')
/**
 * 用途：执行MindMapView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const MindMapView = () => import('../views/MindMapView.vue')
/**
 * 用途：执行ProfileView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const ProfileView = () => import('../views/ProfileView.vue')
/**
 * 用途：执行SettingsView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const SettingsView = () => import('../views/SettingsView.vue')
/**
 * 用途：执行AboutView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const AboutView = () => import('../views/AboutView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/register', component: RegisterView },
    {
      path: '/',
      component: AppShell,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/notes' },
        { path: 'notes', component: NoteListView },
        { path: 'notes/new', component: NoteEditorView },
        { path: 'notes/:id', component: NoteEditorView },
        { path: 'chat', component: ChatView },
        { path: 'chat/session/:sessionId', component: ChatView },
        { path: 'chat/project/:projectId', component: ChatView },
        { path: 'chat/project/:projectId/session/:sessionId', component: ChatView },
        { path: 'chat/:sessionId', component: ChatView },
        { path: 'sessions', redirect: '/chat' },
        { path: 'knowledge', component: KnowledgeView },
        { path: 'knowledge/:id', component: KnowledgeDetailView },
        { path: 'quick-test', component: QuickTestView },
        { path: 'mindmap', component: MindMapView },
        { path: 'profile', component: ProfileView },
        { path: 'settings', component: SettingsView },
        { path: 'about', component: AboutView },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !getJwtToken()) {
    return '/login'
  }
  return true
})

export default router
