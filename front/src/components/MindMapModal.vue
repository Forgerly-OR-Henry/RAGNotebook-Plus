<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Sparkles, X } from '@lucide/vue'
import { mindmapApi } from '../api/mindmaps'
import type { MindMapResponse } from '../types/api'
import MindMapCanvas from './MindMapCanvas.vue'

const props = defineProps<{
  open: boolean
  noteIds: string[]
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const loading = ref(false)
const errorMessage = ref('')
const mindmap = ref<MindMapResponse | null>(null)
const noteKey = computed(() => props.noteIds.join('|'))

watch([() => props.open, noteKey], ([open]) => {
  if (open) {
    void generateMindMap()
  }
}, { immediate: true })

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

function resolveErrorMessage(error: unknown) {
  const detail = error as { message?: string; response?: { data?: { detail?: string; message?: string } } }
  return detail.response?.data?.message || detail.response?.data?.detail || detail.message || '思维导图生成失败，请稍后重试。'
}

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
