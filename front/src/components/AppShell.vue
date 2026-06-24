<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
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

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const collapsed = ref(false)
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const navItems = [
  { path: '/notes', label: '笔记', icon: FileText },
  { path: '/knowledge', label: '知识库', icon: Library },
  { path: '/chat', label: 'AI 问答', icon: MessageSquare },
  { path: '/mindmap', label: '思维导图', icon: Map },
  { path: '/quick-test', label: '快速测试', icon: BookOpenCheck },
]

const bottomItems = [
  { path: '/profile', label: '资料', icon: User },
  { path: '/settings', label: '设置', icon: Settings },
  { path: '/about', label: '关于', icon: Info },
]

/**
 * 用途：执行pageTitle相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const pageTitle = computed(() => {
  if (route.path === '/notes/new') {
    return '新建笔记'
  }
  if (route.path.startsWith('/notes/') && route.path !== '/notes') {
    return '编辑笔记'
  }
  /**
   * 用途：执行item相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const item = [...navItems, ...bottomItems].find((entry) => route.path.startsWith(entry.path))
  return item?.label || '云笺集'
})

/**
 * 用途：执行showBackButton相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const showBackButton = computed(() => (
  (route.path.startsWith('/notes/') && route.path !== '/notes')
  || (route.path.startsWith('/knowledge/') && route.path !== '/knowledge')
))

/**
 * 用途：执行fallbackBackPath相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const fallbackBackPath = computed(() => {
  if (route.path.startsWith('/notes/') && route.path !== '/notes') {
    return '/notes'
  }
  if (route.path.startsWith('/knowledge/') && route.path !== '/knowledge') {
    return '/knowledge'
  }
  return '/chat'
})

/**
 * 用途：执行goBack相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function goBack() {
  const historyState = window.history.state as { back?: string | null }
  if (historyState?.back) {
    router.back()
    return
  }
  router.push(fallbackBackPath.value)
}

/**
 * 用途：执行logout相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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
      class="app-shell__sidebar fixed inset-y-0 left-0 z-20 flex flex-col border-r border-[var(--color-border)] bg-[var(--color-card)]"
      :class="{ 'is-collapsed': collapsed }"
    >
      <div class="app-shell__brand-row flex h-16 items-center px-4">
        <span class="app-shell__brand-clip">
          <span class="app-shell__brand-text font-heading text-lg font-semibold">云笺集</span>
        </span>
        <button
          class="app-shell__collapse-button rounded-md p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
          :title="collapsed ? '展开侧栏' : '收起侧栏'"
          :aria-expanded="!collapsed"
          aria-label="切换侧栏"
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
          class="app-shell__nav-link flex items-center rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
          :class="{ 'is-active': route.path.startsWith(item.path) }"
          :title="collapsed ? item.label : undefined"
        >
          <span class="app-shell__nav-icon">
            <component :is="item.icon" :size="18" />
          </span>
          <span class="app-shell__label-clip">
            <span class="app-shell__nav-label">{{ item.label }}</span>
          </span>
        </RouterLink>
      </nav>

      <div class="space-y-1 border-t border-[var(--color-border)] px-3 py-3">
        <RouterLink
          v-for="item in bottomItems"
          :key="item.path"
          :to="item.path"
          class="app-shell__nav-link flex items-center rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]"
          :class="{ 'is-active': route.path.startsWith(item.path) }"
          :title="collapsed ? item.label : undefined"
        >
          <span class="app-shell__nav-icon">
            <component :is="item.icon" :size="18" />
          </span>
          <span class="app-shell__label-clip">
            <span class="app-shell__nav-label">{{ item.label }}</span>
          </span>
        </RouterLink>
        <button
          class="app-shell__nav-link app-shell__logout flex w-full items-center rounded-md px-3 py-2.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-danger)]"
          :title="collapsed ? '退出' : undefined"
          @click="logout"
        >
          <span class="app-shell__nav-icon">
            <LogOut :size="18" />
          </span>
          <span class="app-shell__label-clip">
            <span class="app-shell__nav-label">退出</span>
          </span>
        </button>
      </div>
    </aside>

    <main class="app-shell__main theme-transition min-h-screen" :class="{ 'is-collapsed': collapsed }">
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

<style scoped>
.app-shell__sidebar {
  width: 15rem;
  transition: width 420ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow 260ms ease;
  will-change: width;
}

.app-shell__sidebar.is-collapsed {
  width: 4rem;
}

.app-shell__brand-row {
  gap: 0.5rem;
  justify-content: space-between;
  overflow: hidden;
  transition: padding 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell__sidebar.is-collapsed .app-shell__brand-row {
  justify-content: center;
  padding-left: 0.75rem;
  padding-right: 0.75rem;
}

.app-shell__brand-clip {
  display: block;
  flex: 1 1 9rem;
  max-width: 9rem;
  min-width: 0;
  overflow: hidden;
  clip-path: inset(0 0 0 0);
  transition:
    flex-basis 420ms cubic-bezier(0.22, 1, 0.36, 1),
    max-width 420ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease,
    clip-path 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell__brand-text,
.app-shell__nav-label {
  display: block;
  white-space: nowrap;
  transform-origin: left center;
  transition:
    transform 420ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease,
    filter 220ms ease;
}

.app-shell__sidebar.is-collapsed .app-shell__brand-clip {
  flex: 0 0 0;
  max-width: 0;
  opacity: 0;
  clip-path: inset(0 100% 0 0);
}

.app-shell__sidebar.is-collapsed .app-shell__brand-text {
  opacity: 0;
  filter: blur(0.8px);
  transform: translate3d(-0.75rem, 70%, 0) scale(0.96);
}

.app-shell__collapse-button {
  flex: 0 0 auto;
  transition:
    color 180ms ease,
    background-color 180ms ease,
    transform 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell__nav-link {
  position: relative;
  min-height: 2.5rem;
  gap: 0.75rem;
  overflow: hidden;
  transition:
    gap 420ms cubic-bezier(0.22, 1, 0.36, 1),
    padding 420ms cubic-bezier(0.22, 1, 0.36, 1),
    color 180ms ease,
    background-color 180ms ease;
}

.app-shell__nav-link.is-active {
  background: var(--color-accent-bg);
  color: var(--color-accent);
}

.app-shell__nav-icon {
  position: relative;
  z-index: 1;
  display: inline-flex;
  width: 1.5rem;
  flex: 0 0 1.5rem;
  align-items: center;
  justify-content: center;
  transition:
    width 420ms cubic-bezier(0.22, 1, 0.36, 1),
    flex-basis 420ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell__label-clip {
  display: block;
  flex: 1 1 auto;
  max-width: 8.5rem;
  min-width: 0;
  overflow: hidden;
  clip-path: inset(0 0 0 0);
  transition:
    max-width 420ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease,
    clip-path 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell__sidebar.is-collapsed .app-shell__nav-link {
  gap: 0;
  padding-left: 0.6875rem;
  padding-right: 0.6875rem;
}

.app-shell__sidebar.is-collapsed .app-shell__nav-icon {
  width: 1.125rem;
  flex-basis: 1.125rem;
}

.app-shell__sidebar.is-collapsed .app-shell__label-clip {
  flex: 0 1 0;
  max-width: 0;
  opacity: 0;
  clip-path: inset(0 100% 0 0);
}

.app-shell__sidebar.is-collapsed .app-shell__nav-label {
  opacity: 0;
  filter: blur(0.7px);
  transform: translate3d(-0.875rem, 0.875rem, 0) scale(0.94);
}

.app-shell__logout {
  justify-content: flex-start;
  text-align: left;
}

.app-shell__logout .app-shell__label-clip {
  flex: 0 1 auto;
  max-width: none;
}

.app-shell__main {
  margin-left: 15rem;
  transition: margin-left 420ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: margin-left;
}

.app-shell__main.is-collapsed {
  margin-left: 4rem;
}

@media (prefers-reduced-motion: reduce) {
  .app-shell__sidebar,
  .app-shell__brand-row,
  .app-shell__brand-clip,
  .app-shell__brand-text,
  .app-shell__collapse-button,
  .app-shell__nav-link,
  .app-shell__nav-icon,
  .app-shell__label-clip,
  .app-shell__nav-label,
  .app-shell__main {
    transition-duration: 0.01ms !important;
  }

  .app-shell__sidebar.is-collapsed .app-shell__brand-text,
  .app-shell__sidebar.is-collapsed .app-shell__nav-label {
    filter: none;
  }
}
</style>
