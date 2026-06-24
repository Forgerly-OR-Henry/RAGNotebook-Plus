<!--
模块职责：Vue 页面组件，负责组合业务 API、页面状态和用户交互。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { useUserStore } from '../stores/useUserStore'

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const username = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const email = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const password = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const error = ref('')
const router = useRouter()
const userStore = useUserStore()

/**
 * 用途：执行submit相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function submit() {
  error.value = ''
  try {
    const data = await authApi.register({
      username: username.value,
      email: email.value,
      password: password.value,
      confirm_password: password.value,
    })
    userStore.login(data.token, data.user)
    router.push('/notes')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败'
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-[var(--color-bg)] px-4">
    <form class="w-full max-w-sm rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-6" @submit.prevent="submit">
      <h1 class="font-heading text-2xl font-semibold">创建账号</h1>
      <div class="mt-6 space-y-4">
        <input v-model="username" placeholder="用户名" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
        <input v-model="email" placeholder="邮箱" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
        <input v-model="password" type="password" placeholder="密码" class="w-full rounded-md border border-[var(--color-border)] bg-transparent px-3 py-2" />
      </div>
      <p v-if="error" class="mt-3 text-sm text-[var(--color-danger)]">{{ error }}</p>
      <button class="mt-6 w-full rounded-md bg-[var(--color-accent)] px-4 py-2 text-white">注册</button>
      <RouterLink class="mt-4 block text-center text-sm text-[var(--color-accent)]" to="/login">返回登录</RouterLink>
    </form>
  </main>
</template>
