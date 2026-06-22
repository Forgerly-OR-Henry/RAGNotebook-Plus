<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  BookOpenCheck,
  Brain,
  FileText,
  GraduationCap,
  History,
  Library,
  LogOut,
  Map,
  MessageSquare,
  Settings,
  User,
} from '@lucide/vue'
import { useUserStore } from '../stores/useUserStore'
import { authApi } from '../api/auth'

const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const navItems = [
  { path: '/notes', label: '笔记', icon: FileText },
  { path: '/knowledge', label: '知识库', icon: Library },
  { path: '/chat', label: 'AI 问答', icon: MessageSquare },
  { path: '/quick-test', label: '快速测试', icon: BookOpenCheck },
  { path: '/mindmap', label: '思维导图', icon: Map },
  { path: '/review', label: '每日回顾', icon: GraduationCap },
  { path: '/sessions', label: '会话', icon: History },
]

const bottomItems = [
  { path: '/profile', label: '资料', icon: User },
  { path: '/settings', label: '设置', icon: Settings },
  { path: '/about', label: '关于', icon: Brain },
]

const pageTitle = computed(() => {
  const item = [...navItems, ...bottomItems].find((entry) => route.path.startsWith(entry.path))
  return item?.label || '云笺集'
})

async function logout() {
  try {
    await authApi.logout()
  } catch {
    // Token may already be expired; local logout should still proceed.
  }
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
    <aside
      class="fixed inset-y-0 left-0 z-20 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-card)] transition-all"
      :class="collapsed ? 'w-16' : 'w-60'"
    >
      <div class="flex h-16 items-center justify-between px-4">
        <span v-if="!collapsed" class="font-heading text-lg font-semibold">云笺集</span>
        <button class="rounded-md px-2 py-1 text-sm hover:bg-[var(--color-bg-secondary)]" @click="collapsed = !collapsed">
          {{ collapsed ? '>' : '<' }}
        </button>
      </div>

      <nav class="flex-1 space-y-1 px-3">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
          :class="{ 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]': route.path.startsWith(item.path), 'justify-center': collapsed }"
        >
          <component :is="item.icon" :size="18" />
          <span v-if="!collapsed">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="space-y-1 border-t border-[var(--color-border)] px-3 py-3">
        <RouterLink
          v-for="item in bottomItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
          :class="{ 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]': route.path.startsWith(item.path), 'justify-center': collapsed }"
        >
          <component :is="item.icon" :size="18" />
          <span v-if="!collapsed">{{ item.label }}</span>
        </RouterLink>
        <button
          class="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-danger)]"
          :class="{ 'justify-center': collapsed }"
          @click="logout"
        >
          <LogOut :size="18" />
          <span v-if="!collapsed">退出</span>
        </button>
      </div>
    </aside>

    <main class="min-h-screen transition-all" :class="collapsed ? 'ml-16' : 'ml-60'">
      <header class="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg)] px-8">
        <h1 class="font-heading text-xl font-semibold">{{ pageTitle }}</h1>
        <div class="text-sm text-[var(--color-text-secondary)]">{{ userStore.userInfo?.username || 'user' }}</div>
      </header>
      <section class="px-8 py-6">
        <RouterView />
      </section>
    </main>
  </div>
</template>
