import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../components/AppShell.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import NoteListView from '../views/NoteListView.vue'
import NoteEditorView from '../views/NoteEditorView.vue'
import ChatView from '../views/ChatView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'
import KnowledgeDetailView from '../views/KnowledgeDetailView.vue'
import QuickTestView from '../views/QuickTestView.vue'
import MindMapView from '../views/MindMapView.vue'
import ProfileView from '../views/ProfileView.vue'
import SettingsView from '../views/SettingsView.vue'
import AboutView from '../views/AboutView.vue'

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
  if (to.meta.requiresAuth && !localStorage.getItem('jwt_token')) {
    return '/login'
  }
  return true
})

export default router
