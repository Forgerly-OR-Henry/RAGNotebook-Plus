<!--
模块职责：Vue 可复用组件，负责封装局部界面、交互状态和事件输出。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { ChevronDown, ChevronUp, FileText, Library, X } from '@lucide/vue'
import { notesApi } from '../api/notes'
import type { RelatedFragment } from '../types/api'

// 组件入参：由父组件传入业务对象、加载态和展示模式。
const props = defineProps<{
  noteId: string
  open: boolean
}>()

// 组件事件：向父组件报告关闭、保存、选择等交互结果。
const emit = defineEmits<{
  close: []
}>()

const fragments = ref<RelatedFragment[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
const expandedId = ref<string | null>(null)

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(
  () => [props.open, props.noteId] as const,
  async ([open, noteId]) => {
    if (!open || !noteId) return
    loading.value = true
    try {
      const res = await notesApi.related(noteId)
      fragments.value = res.data ?? []
    } catch {
      fragments.value = []
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <aside v-if="open" class="flex w-80 shrink-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-card)]">
    <div class="flex h-12 items-center justify-between border-b border-[var(--color-border-light)] px-4">
      <h2 class="text-sm font-medium text-[var(--color-text)]">
        关联片段
        <span v-if="!loading" class="ml-1.5 text-xs text-[var(--color-text-tertiary)]">({{ fragments.length }})</span>
      </h2>
      <button class="rounded-md p-1 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" aria-label="关闭关联片段" @click="emit('close')">
        <X :size="16" />
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="loading" class="flex justify-center py-12">
        <div class="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
      </div>
      <div v-else-if="fragments.length === 0" class="px-4 py-12 text-center text-sm text-[var(--color-text-tertiary)]">暂无关联片段</div>
      <div v-else class="space-y-3 p-3">
        <article
          v-for="fragment in fragments"
          :key="`${fragment.source}-${fragment.id}-${fragment.content_preview.slice(0, 20)}`"
          class="overflow-hidden rounded-md border border-[var(--color-border-light)] bg-[var(--color-bg)]"
        >
          <button class="w-full px-3 pb-2 pt-3 text-left hover:bg-[var(--color-bg-secondary)]" type="button" @click="expandedId = expandedId === fragment.id ? null : fragment.id">
            <div class="flex items-start justify-between gap-2">
              <div class="flex min-w-0 items-center gap-1.5">
                <Library v-if="fragment.source === 'knowledge_base'" :size="13" class="shrink-0 text-blue-500" />
                <FileText v-else :size="13" class="shrink-0 text-emerald-500" />
                <span class="truncate text-xs font-medium text-[var(--color-text)]">{{ fragment.title }}</span>
              </div>
              <div class="flex shrink-0 items-center gap-1">
                <span
                  class="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                  :class="fragment.source === 'knowledge_base' ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'"
                >
                  {{ fragment.source === 'knowledge_base' ? '知识库' : '笔记' }}
                </span>
                <ChevronUp v-if="expandedId === fragment.id" :size="14" class="text-[var(--color-text-tertiary)]" />
                <ChevronDown v-else :size="14" class="text-[var(--color-text-tertiary)]" />
              </div>
            </div>
            <p class="mt-1.5 line-clamp-3 text-xs leading-relaxed text-[var(--color-text-secondary)]">{{ fragment.content_preview }}</p>
            <div class="mt-1 text-[10px] text-[var(--color-text-tertiary)]">相似度: {{ (fragment.similarity * 100).toFixed(1) }}%</div>
          </button>
          <div v-if="expandedId === fragment.id" class="border-t border-[var(--color-border-light)] px-3 pb-3 pt-1">
            <p class="max-h-60 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-[var(--color-text-secondary)]">{{ fragment.content }}</p>
          </div>
        </article>
      </div>
    </div>
  </aside>
</template>
