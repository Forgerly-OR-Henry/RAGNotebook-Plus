import { createRouter, createWebHistory } from 'vue-router'
import { getJwtToken } from '../api/authToken'
import AppShell from '../components/AppShell.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'

const NoteListView = () => import('../views/NoteListView.vue')
const NoteEditorView = () => import('../views/NoteEditorView.vue')
const ChatView = () => import('../views/ChatView.vue')
const KnowledgeView = () => import('../views/KnowledgeView.vue')
const KnowledgeDetailView = () => import('../views/KnowledgeDetailView.vue')
const QuickTestView = () => import('../views/QuickTestView.vue')
const MindMapView = () => import('../views/MindMapView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const SettingsView = () => import('../views/SettingsView.vue')
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
