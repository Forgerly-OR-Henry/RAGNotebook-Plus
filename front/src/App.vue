<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import { LoaderCircle, RefreshCw, ServerCrash } from '@lucide/vue'
import { healthApi, type ReadinessStatus } from './api/health'

const POLL_INTERVAL_MS = 1500

const readiness = ref<ReadinessStatus | null>(null)
const isReady = ref(false)
const isChecking = ref(true)
const connectionError = ref('')
let pollTimer: number | undefined

const componentStates = computed(() => {
  const components = readiness.value?.checks.model_runtime.components
  return [
    { key: 'models', label: 'AI 模型', ready: Boolean(components?.models) },
    { key: 'note_service', label: '笔记索引', ready: Boolean(components?.note_service) },
    { key: 'reranker', label: '重排序', ready: Boolean(components?.reranker) },
  ]
})

const readyCount = computed(() => componentStates.value.filter((item) => item.ready).length)

const readinessTitle = computed(() => {
  if (readiness.value?.status === 'failed') {
    return '初始化失败'
  }
  if (connectionError.value) {
    return '正在连接后端'
  }
  return '系统初始化中'
})

const readinessMessage = computed(() => {
  const runtime = readiness.value?.checks.model_runtime
  if (runtime?.status === 'failed') {
    return runtime.error || '后台模型初始化失败，请检查后端日志。'
  }
  if (connectionError.value) {
    return connectionError.value
  }
  return `正在准备模型服务，已完成 ${readyCount.value}/${componentStates.value.length} 项。`
})

const statusIcon = computed(() => (readiness.value?.status === 'failed' ? ServerCrash : LoaderCircle))
const shouldShowRetry = computed(() => Boolean(connectionError.value) || readiness.value?.status === 'failed')

function stopPolling() {
  if (pollTimer === undefined) {
    return
  }
  window.clearInterval(pollTimer)
  pollTimer = undefined
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(() => {
    void checkReadiness()
  }, POLL_INTERVAL_MS)
}

async function checkReadiness() {
  isChecking.value = true
  try {
    const data = await healthApi.getReadiness()
    readiness.value = data
    connectionError.value = ''
    isReady.value = data.status === 'ok'
    if (data.status === 'ok' || data.status === 'failed') {
      stopPolling()
    }
  } catch (error) {
    readiness.value = null
    isReady.value = false
    connectionError.value = error instanceof Error && error.message ? error.message : '后端服务暂未就绪。'
  } finally {
    isChecking.value = false
  }
}

function retryReadiness() {
  void checkReadiness()
  startPolling()
}

onMounted(() => {
  void checkReadiness()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <RouterView v-if="isReady" />
  <div v-else class="flex min-h-screen items-center justify-center bg-[var(--color-bg)] px-6 text-[var(--color-text)]">
    <section class="w-full max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 shadow-sm">
      <div class="flex items-start gap-4">
        <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
          <component :is="statusIcon" :size="24" :class="{ 'animate-spin': readiness?.status !== 'failed' }" />
        </div>
        <div class="min-w-0 flex-1">
          <h1 class="font-heading text-xl font-semibold">{{ readinessTitle }}</h1>
          <p class="mt-2 text-sm leading-6 text-[var(--color-text-secondary)]">{{ readinessMessage }}</p>
        </div>
      </div>

      <div class="mt-6 space-y-3">
        <div
          v-for="item in componentStates"
          :key="item.key"
          class="flex items-center justify-between rounded-md border border-[var(--color-border-light)] px-3 py-2 text-sm"
        >
          <span class="text-[var(--color-text)]">{{ item.label }}</span>
          <span :class="item.ready ? 'text-[var(--color-success)]' : 'text-[var(--color-text-tertiary)]'">
            {{ item.ready ? '就绪' : '等待中' }}
          </span>
        </div>
      </div>

      <button
        v-if="shouldShowRetry"
        class="mt-6 inline-flex h-9 items-center gap-2 rounded-md bg-[var(--color-accent)] px-3 text-sm font-medium text-white disabled:opacity-60"
        type="button"
        :disabled="isChecking"
        @click="retryReadiness"
      >
        <RefreshCw :size="16" :class="{ 'animate-spin': isChecking }" />
        重试
      </button>
    </section>
  </div>
</template>
