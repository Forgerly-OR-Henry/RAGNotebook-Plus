<!--
模块职责：Vue 页面组件，负责组合业务 API、页面状态和用户交互。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { useUserStore } from '../stores/useUserStore'

/**
 * 用途：执行envBool相关业务逻辑。
 * @param name 调用方传入的name参数，用于驱动当前前端逻辑。
 * @param defaultValue 调用方传入的defaultValue参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function envBool(name: string, defaultValue: boolean) {
  const value = String(import.meta.env[name] ?? '').trim().toLowerCase()
  if (!value) {
    return defaultValue
  }
  if (['1', 'true', 'yes', 'on'].includes(value)) {
    return true
  }
  if (['0', 'false', 'no', 'off'].includes(value)) {
    return false
  }
  throw new Error(`${name} must be a boolean value`)
}

const loginPrefillEnabled = envBool('VITE_LOGIN_PREFILL_ENABLED', false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const username = ref(loginPrefillEnabled ? 'admin' : '')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const password = ref(loginPrefillEnabled ? 'admin1234' : '')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const error = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
const router = useRouter()
const userStore = useUserStore()

/**
 * 用途：执行submit相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function submit() {
  loading.value = true
  error.value = ''
  try {
    const data = await authApi.login(username.value, password.value)
    userStore.login(data.token, data.user)
    router.push('/notes')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-[var(--color-bg)] px-4">
    <form class="w-full max-w-sm rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-6" @submit.prevent="submit">
      <h1 class="font-heading text-2xl font-semibold">云笺集</h1>
      <div class="mt-6 space-y-4">
        <label class="block text-sm">
          <span class="text-[var(--color-text-secondary)]">用户名</span>
          <input v-model="username" class="mt-1 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
        </label>
        <label class="block text-sm">
          <span class="text-[var(--color-text-secondary)]">密码</span>
          <input v-model="password" type="password" class="mt-1 w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
        </label>
      </div>
      <p v-if="error" class="mt-3 text-sm text-[var(--color-danger)]">{{ error }}</p>
      <button class="mt-6 w-full rounded-md bg-[var(--color-accent)] px-4 py-2 text-white disabled:opacity-60" :disabled="loading">
        {{ loading ? '登录中' : '登录' }}
      </button>
      <RouterLink class="mt-4 block text-center text-sm text-[var(--color-accent)]" to="/register">注册账号</RouterLink>
    </form>
  </main>
</template>
