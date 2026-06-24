<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, Brain, Check, ChevronRight, Database, FileText, Folder, Loader2, Search, Sparkles } from '@lucide/vue'
import { knowledgeApi } from '../api/knowledge'
import { mindmapApi } from '../api/mindmaps'
import { notesApi } from '../api/notes'
import MindMapCanvas from '../components/MindMapCanvas.vue'
import { buildFolderTreeRows, type FolderTreeFile } from '../features/sources/folderTree'
import type { KnowledgeDocument, KnowledgeFolder, MindMapResponse, MindMapSourceType, Note, NoteFolder } from '../types/api'

type Step = 'selection' | 'generating' | 'canvas'

const notes = ref<Note[]>([])
const docs = ref<KnowledgeDocument[]>([])
const noteFolders = ref<NoteFolder[]>([])
const knowledgeFolders = ref<KnowledgeFolder[]>([])
const sourceType = ref<MindMapSourceType>('note')
const selectedSourceIds = ref<Set<string>>(new Set())
const collapsedFolderKeys = ref<Record<MindMapSourceType, Set<string>>>({
  note: new Set(),
  knowledge: new Set(),
})
const focus = ref('')
const searchQuery = ref('')
const mindmap = ref<MindMapResponse | null>(null)
const step = ref<Step>('selection')
const loadingSources = ref(false)
const errorMessage = ref('')
const generatingMessage = ref('正在读取内容...')
let generatingTimer: number | undefined

const sourceFiles = computed<FolderTreeFile[]>(() => {
  if (sourceType.value === 'note') {
    return notes.value
      .filter((note) => note.id)
      .map((note) => ({
        id: note.id,
        folderId: note.folder_id,
        title: note.title || '无标题',
        subtitle: `${note.category || '未分类'} · ${formatDate(note.updated_at || note.created_at)}`,
        searchText: [note.title, note.category, ...(note.tags || [])].filter(Boolean).join(' '),
      }))
  }

  return docs.value
    .map((doc) => {
      const title = doc.original_filename || doc.title || doc.filename || '未命名文档'
      return {
        id: doc.id || doc.document_id || '',
        folderId: doc.folder_id,
        title,
        subtitle: `${doc.status || 'ready'} · ${doc.chunk_count || 0} 个片段`,
        searchText: [title, doc.status, doc.category, ...(doc.tags || [])].filter(Boolean).join(' '),
      }
    })
    .filter((item) => item.id)
})

const sourceRows = computed(() => buildFolderTreeRows(
  sourceType.value === 'note' ? noteFolders.value : knowledgeFolders.value,
  sourceFiles.value,
  sourceType.value === 'note' ? '暂无可用笔记' : '暂无可用文档',
  searchQuery.value,
  collapsedFolderKeys.value[sourceType.value],
  true,
))

const visibleSourceIds = computed(() => sourceRows.value
  .filter((item) => item.kind === 'file' && item.sourceId)
  .map((item) => item.sourceId as string))

const selectedIds = computed(() => Array.from(selectedSourceIds.value))
const allVisibleSelected = computed(() => visibleSourceIds.value.length > 0 && visibleSourceIds.value.every((id) => selectedSourceIds.value.has(id)))

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
    const [noteRes, docRes, noteFolderRes, knowledgeFolderRes] = await Promise.all([
      notesApi.list({ page: 1, page_size: 100 }),
      knowledgeApi.list(),
      notesApi.listFolders(),
      knowledgeApi.listFolders(),
    ])
    notes.value = noteRes.data.notes
    docs.value = docRes.data.documents
    noteFolders.value = noteFolderRes.data.folders
    knowledgeFolders.value = knowledgeFolderRes.data.folders
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

function toggleSourceSelection(id: string) {
  const next = new Set(selectedSourceIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  selectedSourceIds.value = next
}

function toggleAllVisible() {
  const next = new Set(selectedSourceIds.value)
  if (allVisibleSelected.value) {
    visibleSourceIds.value.forEach((id) => next.delete(id))
  } else {
    visibleSourceIds.value.forEach((id) => next.add(id))
  }
  selectedSourceIds.value = next
}

function isFolderCollapsed(key: string) {
  if (searchQuery.value.trim()) return false
  return !collapsedFolderKeys.value[sourceType.value].has(key)
}

function toggleFolder(key: string) {
  const next = new Set(collapsedFolderKeys.value[sourceType.value])
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  collapsedFolderKeys.value = {
    ...collapsedFolderKeys.value,
    [sourceType.value]: next,
  }
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
          <button class="rounded-md border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50" type="button" :disabled="visibleSourceIds.length === 0" @click="toggleAllVisible">
            {{ allVisibleSelected ? '取消全选' : '全选当前' }}
          </button>
        </div>

        <div class="max-h-[460px] overflow-y-auto p-2">
          <div v-if="loadingSources" class="flex items-center justify-center gap-2 py-12 text-sm text-[var(--color-text-secondary)]">
            <Loader2 :size="18" class="animate-spin" />
            加载中
          </div>
          <template v-else>
            <div
              v-for="row in sourceRows"
              :key="row.key"
              class="mb-1 last:mb-0"
            >
              <p v-if="row.kind === 'empty'" class="py-12 text-center text-sm text-[var(--color-text-secondary)]">{{ row.title }}</p>
              <button
                v-else-if="row.kind === 'folder'"
                class="flex min-h-9 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
                type="button"
                :aria-expanded="!isFolderCollapsed(row.key)"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="toggleFolder(row.key)"
              >
                <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform" :class="{ 'rotate-90': !isFolderCollapsed(row.key) }" />
                <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </button>
              <button
                v-else
                class="flex min-h-12 w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-bg-secondary)]"
                :class="row.sourceId && selectedSourceIds.has(row.sourceId) ? 'border-[var(--color-accent)] bg-[var(--color-accent-bg)]/60' : 'border-transparent'"
                type="button"
                :aria-pressed="row.sourceId ? selectedSourceIds.has(row.sourceId) : false"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="row.sourceId && toggleSourceSelection(row.sourceId)"
              >
                <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-[var(--color-border)]" :class="{ 'bg-[var(--color-accent)] text-white': row.sourceId && selectedSourceIds.has(row.sourceId) }">
                  <Check v-if="row.sourceId && selectedSourceIds.has(row.sourceId)" :size="14" />
                </span>
                <FileText v-if="sourceType === 'note'" :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                <Database v-else :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium text-[var(--color-text)]">{{ row.title }}</span>
                  <span v-if="row.subtitle" class="mt-0.5 block truncate text-xs text-[var(--color-text-tertiary)]">{{ row.subtitle }}</span>
                </span>
              </button>
            </div>
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
