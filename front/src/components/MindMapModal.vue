<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Sparkles, X } from '@lucide/vue'
import { mindmapApi } from '../api/mindmaps'
import type { MindMapResponse } from '../types/api'
import MindMapCanvas from './MindMapCanvas.vue'

// 组件入参：由父组件传入业务对象、加载态和展示模式。
const props = defineProps<{
  open: boolean
  noteIds: string[]
}>()

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const errorMessage = ref('')
const mindmap = ref<MindMapResponse | null>(null)
/**
 * 用途：执行noteKey相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const noteKey = computed(() => props.noteIds.join('|'))

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch([() => props.open, noteKey], ([open]) => {
  if (open) {
    void generateMindMap()
  }
}, { immediate: true })

/**
 * 用途：执行generateMindMap相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function generateMindMap() {
  errorMessage.value = ''
  mindmap.value = null
  if (props.noteIds.length === 0) {
    errorMessage.value = '请先选择笔记。'
    return
  }

  loading.value = true
  try {
    mindmap.value = await mindmapApi.generate({
      source_type: 'note',
      source_ids: props.noteIds,
      max_nodes: 60,
      max_depth: 4,
    })
  } catch (error) {
    errorMessage.value = resolveErrorMessage(error)
  } finally {
    loading.value = false
  }
}

/**
 * 用途：执行resolveErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function resolveErrorMessage(error: unknown) {
  const detail = error as { message?: string; response?: { data?: { detail?: string; message?: string } } }
  return detail.response?.data?.message || detail.response?.data?.detail || detail.message || '思维导图生成失败，请稍后重试。'
}

/**
 * 用途：执行close相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function close() {
  emit('update:open', false)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm" @click.self="close">
      <section class="flex h-[90vh] w-full max-w-7xl flex-col overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] shadow-2xl">
        <header class="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4">
          <div class="flex items-center gap-2">
            <Sparkles :size="18" class="text-[var(--color-accent)]" />
            <div>
              <h3 class="text-sm font-semibold text-[var(--color-text)]">AI 笔记思维导图</h3>
              <p class="text-xs text-[var(--color-text-tertiary)]">已选择 {{ noteIds.length }} 篇笔记</p>
            </div>
          </div>
          <button class="rounded-md border border-[var(--color-border)] p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="关闭" @click="close">
            <X :size="15" />
          </button>
        </header>

        <p v-if="errorMessage" class="mx-5 mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ errorMessage }}</p>

        <div class="min-h-0 flex-1 p-5">
          <MindMapCanvas
            :mindmap="mindmap"
            :loading="loading"
            empty-text="暂无导图结果。"
          />
        </div>
      </section>
    </div>
  </Teleport>
</template>
