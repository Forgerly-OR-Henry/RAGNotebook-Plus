<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, Brain, Database, FileText, Loader2, Search, Sparkles } from '@lucide/vue'
import { knowledgeApi } from '../api/knowledge'
import { mindmapApi } from '../api/mindmaps'
import { notesApi } from '../api/notes'
import MindMapCanvas from '../components/MindMapCanvas.vue'
import type { KnowledgeDocument, MindMapResponse, MindMapSourceType, Note } from '../types/api'

type Step = 'selection' | 'generating' | 'canvas'

interface SourceOption {
  id: string
  title: string
  subtitle: string
}

const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const sourceType = ref<MindMapSourceType>('note')
const selectedSourceIds = ref<Set<string>>(new Set())
const focus = ref('')
const searchQuery = ref('')
const mindmap = ref<MindMapResponse | null>(null)
const step = ref<Step>('selection')
const loadingSources = ref(false)
const errorMessage = ref('')
const generatingMessage = ref('正在读取内容...')
let generatingTimer: number | undefined

const sourceOptions = computed<SourceOption[]>(() => {
  if (sourceType.value === 'note') {
    return notes.value
      .filter((note) => note.id)
      .map((note) => ({
        id: note.id,
        title: note.title || '无标题',
        subtitle: `${note.category || '未分类'} · ${formatDate(note.updated_at || note.created_at)}`,
      }))
  }

  return docs.value
    .map((doc) => ({
      id: doc.id || doc.document_id || '',
      title: doc.original_filename || doc.title || doc.filename || '未命名文档',
      subtitle: `${doc.status || 'ready'} · ${doc.chunk_count || 0} 个片段`,
    }))
    .filter((item) => item.id)
})

const filteredSources = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return sourceOptions.value
  return sourceOptions.value.filter((item) => (
    item.title.toLowerCase().includes(keyword)
    || item.subtitle.toLowerCase().includes(keyword)
  ))
})

const selectedIds = computed(() => Array.from(selectedSourceIds.value))
const allVisibleSelected = computed(() => filteredSources.value.length > 0 && filteredSources.value.every((item) => selectedSourceIds.value.has(item.id)))

watch(sourceType, () => {
  selectedSourceIds.value = new Set()
  searchQuery.value = ''
  errorMessage.value = ''
})

watch(step, (value) => {
  clearGeneratingTimer()
  if (value !== 'generating') return
  const messages = [
    '正在读取内容...',
    '正在分析主题关系...',
    '正在构建层级大纲...',
    '正在绘制思维导图...',
  ]
  let index = 0
  generatingMessage.value = messages[index]
  generatingTimer = window.setInterval(() => {
    index = Math.min(index + 1, messages.length - 1)
    generatingMessage.value = messages[index]
  }, 1800)
})

onMounted(loadSources)

onBeforeUnmount(() => {
  clearGeneratingTimer()
})

async function loadSources() {
  loadingSources.value = true
  errorMessage.value = ''
  try {
    const [noteRes, docRes] = await Promise.all([
      notesApi.list({ page: 1, page_size: 100 }),
      knowledgeApi.list(),
    ])
    notes.value = noteRes.data.notes
    docs.value = docRes.data.documents
  } catch (error) {
    errorMessage.value = resolveErrorMessage(error, '来源加载失败')
  } finally {
    loadingSources.value = false
  }
}

function clearGeneratingTimer() {
  if (generatingTimer) {
    window.clearInterval(generatingTimer)
    generatingTimer = undefined
  }
}

function toggleSource(id: string, checked: boolean) {
  const next = new Set(selectedSourceIds.value)
  if (checked) {
    next.add(id)
  } else {
    next.delete(id)
  }
  selectedSourceIds.value = next
}

function toggleAllVisible() {
  const next = new Set(selectedSourceIds.value)
  if (allVisibleSelected.value) {
    filteredSources.value.forEach((item) => next.delete(item.id))
  } else {
    filteredSources.value.forEach((item) => next.add(item.id))
  }
  selectedSourceIds.value = next
}

async function generate() {
  errorMessage.value = ''
  if (selectedIds.value.length === 0) {
    errorMessage.value = '请先选择来源。'
    return
  }

  step.value = 'generating'
  mindmap.value = null
  try {
    mindmap.value = await mindmapApi.generate({
      source_type: sourceType.value,
      source_ids: selectedIds.value,
      max_nodes: sourceType.value === 'note' ? 60 : 50,
      max_depth: 4,
      focus: focus.value.trim() || undefined,
    })
    step.value = 'canvas'
  } catch (error) {
    errorMessage.value = resolveErrorMessage(error, '思维导图生成失败')
    step.value = 'selection'
  }
}

function backToSelection() {
  step.value = 'selection'
}

function resolveErrorMessage(error: unknown, fallback: string) {
  const detail = error as { message?: string; response?: { data?: { detail?: string; message?: string } } }
  return detail.response?.data?.message || detail.response?.data?.detail || detail.message || fallback
}

function formatDate(value?: string | null) {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知时间'
  return date.toLocaleDateString()
}
</script>

<template>
  <div class="flex min-h-[720px] flex-col">
    <section v-if="step === 'selection'" class="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-5 px-1 py-2">
      <header class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--color-accent-bg)] text-[var(--color-accent)]">
            <Brain :size="22" />
          </div>
          <div>
            <h1 class="font-heading text-2xl font-semibold text-[var(--color-text)]">AI 思维导图</h1>
            <p class="text-xs text-[var(--color-text-tertiary)]">已选择 {{ selectedIds.length }} 项</p>
          </div>
        </div>

        <div class="inline-flex rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-1">
          <button
            class="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs"
            :class="sourceType === 'note' ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'"
            type="button"
            @click="sourceType = 'note'"
          >
            <FileText :size="14" />
            笔记
          </button>
          <button
            class="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs"
            :class="sourceType === 'knowledge' ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'"
            type="button"
            @click="sourceType = 'knowledge'"
          >
            <Database :size="14" />
            知识库
          </button>
        </div>
      </header>

      <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
        <div class="flex flex-wrap items-center gap-3 border-b border-[var(--color-border)] p-4">
          <form class="relative min-w-56 flex-1" @submit.prevent>
            <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-placeholder)]" />
            <input
              v-model="searchQuery"
              class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] py-2 pl-9 pr-4 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="搜索来源"
            />
          </form>
          <input
            v-model="focus"
            class="min-w-56 flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
            placeholder="导图关注点"
          />
          <button class="rounded-md border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" @click="toggleAllVisible">
            {{ allVisibleSelected ? '取消全选' : '全选当前' }}
          </button>
        </div>

        <div class="max-h-[460px] overflow-y-auto p-2">
          <div v-if="loadingSources" class="flex items-center justify-center gap-2 py-12 text-sm text-[var(--color-text-secondary)]">
            <Loader2 :size="18" class="animate-spin" />
            加载中
          </div>
          <p v-else-if="filteredSources.length === 0" class="py-12 text-center text-sm text-[var(--color-text-secondary)]">暂无可用来源</p>
          <template v-else>
            <label
              v-for="item in filteredSources"
              :key="item.id"
              class="mb-2 flex cursor-pointer items-start gap-3 rounded-md border px-3 py-3 transition-colors last:mb-0"
              :class="selectedSourceIds.has(item.id) ? 'border-[var(--color-accent)] bg-[var(--color-accent-bg)]/60' : 'border-transparent hover:bg-[var(--color-bg-secondary)]'"
            >
              <input
                class="mt-1"
                type="checkbox"
                :checked="selectedSourceIds.has(item.id)"
                @change="toggleSource(item.id, ($event.target as HTMLInputElement).checked)"
              />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-[var(--color-text)]">{{ item.title }}</p>
                <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ item.subtitle }}</p>
              </div>
            </label>
          </template>
        </div>
      </div>

      <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ errorMessage }}</p>

      <div class="flex justify-end">
        <button
          class="inline-flex items-center gap-2 rounded-md bg-[var(--color-accent)] px-5 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="selectedIds.length === 0 || loadingSources"
          @click="generate"
        >
          <Sparkles :size="16" />
          生成导图
        </button>
      </div>
    </section>

    <section v-else-if="step === 'generating'" class="flex flex-1 flex-col items-center justify-center gap-5 py-20">
      <div class="flex h-16 w-16 items-center justify-center rounded-md bg-[var(--color-accent)] text-white shadow-sm">
        <Brain :size="30" />
      </div>
      <div class="text-center">
        <h2 class="text-base font-semibold text-[var(--color-text)]">思维导图生成中</h2>
        <p class="mt-1 text-xs text-[var(--color-text-secondary)]">{{ generatingMessage }}</p>
      </div>
    </section>

    <section v-else class="flex min-h-0 flex-1 flex-col gap-3">
      <div class="flex items-center justify-between">
        <button class="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" @click="backToSelection">
          <ArrowLeft :size="14" />
          重新选择
        </button>
      </div>
      <MindMapCanvas :mindmap="mindmap" />
    </section>
  </div>
</template>
