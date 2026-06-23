<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  BookOpenCheck,
  Columns2,
  FileText,
  Library,
  LogOut,
  Map,
  MessageSquare,
  Info,
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
]

const bottomItems = [
  { path: '/profile', label: '资料', icon: User },
  { path: '/settings', label: '设置', icon: Settings },
  { path: '/about', label: '关于', icon: Info },
]

const pageTitle = computed(() => {
  if (route.path === '/notes/new') {
    return '新建笔记'
  }
  if (route.path.startsWith('/notes/') && route.path !== '/notes') {
    return '编辑笔记'
  }
  const item = [...navItems, ...bottomItems].find((entry) => route.path.startsWith(entry.path))
  return item?.label || '云笺集'
})

const showBackButton = computed(() => (
  (route.path.startsWith('/notes/') && route.path !== '/notes')
  || (route.path.startsWith('/knowledge/') && route.path !== '/knowledge')
))

const fallbackBackPath = computed(() => {
  if (route.path.startsWith('/notes/') && route.path !== '/notes') {
    return '/notes'
  }
  if (route.path.startsWith('/knowledge/') && route.path !== '/knowledge') {
    return '/knowledge'
  }
  return '/chat'
})

function goBack() {
  const historyState = window.history.state as { back?: string | null }
  if (historyState?.back) {
    router.back()
    return
  }
  router.push(fallbackBackPath.value)
}

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
  <div class="theme-transition min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
    <aside
      class="fixed inset-y-0 left-0 z-20 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-card)] transition-all"
      :class="collapsed ? 'w-16' : 'w-60'"
    >
      <div class="flex h-16 items-center justify-between px-4">
        <span v-if="!collapsed" class="font-heading text-lg font-semibold">云笺集</span>
        <button
          class="rounded-md p-1.5 text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)]"
          :title="collapsed ? '展开侧栏' : '收起侧栏'"
          @click="collapsed = !collapsed"
        >
          <Columns2 :size="18" class="transition-transform duration-300" :class="{ 'rotate-180': collapsed }" />
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

    <main class="theme-transition min-h-screen transition-all" :class="collapsed ? 'ml-16' : 'ml-60'">
      <header class="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg)] px-8">
        <div class="flex min-w-0 items-center gap-3">
          <button
            v-if="showBackButton"
            class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
            type="button"
            aria-label="返回上一页"
            title="返回上一页"
            @click="goBack"
          >
            <ArrowLeft :size="18" />
          </button>
          <h1 class="truncate font-heading text-xl font-semibold">{{ pageTitle }}</h1>
        </div>
      </header>
      <section class="px-8 py-6">
        <RouterView />
      </section>
    </main>
  </div>
</template>
