<!--
模块职责：Vue 页面组件，负责组合业务 API、页面状态和用户交互。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useUserStore } from '../stores/useUserStore'
import client from '../api/client'
import { endpoints } from '../api/endpoints'

const sessions = ref<string[]>([])
const userStore = useUserStore()

/**
 * 用途：执行load相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function load() {
  const userId = userStore.userInfo?.id || userStore.userInfo?.uuid || userStore.userInfo?.user_id
  if (!userId) return
  const res = await client.get<{ data: { sessions: string[] } }>(endpoints.getUserSessions(userId))
  sessions.value = res.data.data.sessions
}

onMounted(load)
</script>

<template>
  <div class="space-y-3">
    <button class="rounded-md border border-[var(--color-border)] px-4 py-2" @click="load">刷新</button>
    <RouterLink v-for="id in sessions" :key="id" :to="`/chat/${id}`" class="block rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      {{ id }}
    </RouterLink>
  </div>
</template>
