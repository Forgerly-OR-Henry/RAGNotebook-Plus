<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowLeft,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  Database,
  FileText,
  Folder,
  Info,
  Loader2,
  Play,
  RotateCcw,
  Search,
  Sparkles,
  XCircle,
} from '@lucide/vue'
import { chatApi } from '../api/chat'
import { knowledgeApi } from '../api/knowledge'
import { notesApi } from '../api/notes'
import { buildFolderTreeRows, type FolderTreeFile } from '../features/sources/folderTree'
import type { KnowledgeDocument, KnowledgeFolder, Note, NoteFolder, QuizResponse } from '../types/api'

type Step = 'selection' | 'generating' | 'quiz' | 'result'

const step = ref<Step>('selection')
const generatingMessage = ref('正在读取所选内容...')
const notes = ref<Note[]>([])
const documents = ref<KnowledgeDocument[]>([])
const noteFolders = ref<NoteFolder[]>([])
const knowledgeFolders = ref<KnowledgeFolder[]>([])
const loadingContext = ref(true)
const selectedNotes = ref<string[]>([])
const selectedFiles = ref<string[]>([])
const collapsedNoteFolderKeys = ref<Set<string>>(new Set())
const collapsedDocumentFolderKeys = ref<Set<string>>(new Set())
const noteSearch = ref('')
const fileSearch = ref('')
const quiz = ref<QuizResponse | null>(null)
const userAnswers = ref<Record<string, string>>({})
const score = ref(0)
const errorMessage = ref('')

let generationTimer: number | undefined

const noteFiles = computed<FolderTreeFile[]>(() => notes.value.map((note) => ({
  id: note.id,
  folderId: note.folder_id,
  title: note.title || '无标题',
  subtitle: `${note.category || '默认分类'} · ${formatDate(note.updated_at || note.created_at)}`,
  searchText: [note.title, note.category, ...(note.tags || [])].filter(Boolean).join(' '),
})))

const documentFiles = computed<FolderTreeFile[]>(() => documents.value.map((doc) => {
  const title = docTitle(doc)
  return {
    id: doc.id,
    folderId: doc.folder_id,
    title,
    subtitle: `${doc.status || 'ready'} · ${formatFileSize(doc.file_size)}`,
    searchText: [title, doc.status, doc.category, ...(doc.tags || [])].filter(Boolean).join(' '),
  }
}))

const noteRows = computed(() => buildFolderTreeRows(noteFolders.value, noteFiles.value, '暂无可用笔记', noteSearch.value, collapsedNoteFolderKeys.value, true))
const documentRows = computed(() => buildFolderTreeRows(knowledgeFolders.value, documentFiles.value, '暂无可用文档', fileSearch.value, collapsedDocumentFolderKeys.value, true))
const visibleNoteIds = computed(() => noteRows.value.filter((row) => row.kind === 'file' && row.sourceId).map((row) => row.sourceId as string))
const visibleDocumentIds = computed(() => documentRows.value.filter((row) => row.kind === 'file' && row.sourceId).map((row) => row.sourceId as string))
const allNotesSelected = computed(() => visibleNoteIds.value.length > 0 && visibleNoteIds.value.every((id) => selectedNotes.value.includes(id)))
const allDocsSelected = computed(() => visibleDocumentIds.value.length > 0 && visibleDocumentIds.value.every((id) => selectedFiles.value.includes(id)))
const answeredCount = computed(() => quiz.value?.questions.filter((q) => userAnswers.value[q.id]).length || 0)

async function loadData() {
  loadingContext.value = true
  errorMessage.value = ''
  try {
    const [notesRes, docsRes, noteFolderRes, knowledgeFolderRes] = await Promise.all([
      notesApi.list({ page: 1, page_size: 100 }),
      knowledgeApi.list(),
      notesApi.listFolders(),
      knowledgeApi.listFolders(),
    ])
    notes.value = notesRes.data.notes || []
    documents.value = docsRes.data.documents || []
    noteFolders.value = noteFolderRes.data.folders
    knowledgeFolders.value = knowledgeFolderRes.data.folders
  } catch (error) {
    errorMessage.value = messageFromError(error, '加载选项数据失败')
  } finally {
    loadingContext.value = false
  }
}

function startGeneratingMessages() {
  stopGeneratingMessages()
  const messages = [
    '正在提取选中笔记与文件内容...',
    '已定位资料片段，正在分析核心概念...',
    '正在构建单选题与判断题...',
    '正在生成答案解析...',
    '快速测验即将就绪...',
  ]
  let index = 0
  generatingMessage.value = messages[index]
  generationTimer = window.setInterval(() => {
    index = Math.min(index + 1, messages.length - 1)
    generatingMessage.value = messages[index]
  }, 1800)
}

function stopGeneratingMessages() {
  if (generationTimer) {
    window.clearInterval(generationTimer)
    generationTimer = undefined
  }
}

async function handleGenerate() {
  errorMessage.value = ''
  if (!selectedNotes.value.length && !selectedFiles.value.length) {
    errorMessage.value = '请至少选择一篇笔记或一个知识库文档'
    return
  }

  step.value = 'generating'
  startGeneratingMessages()
  try {
    const res = await chatApi.generateQuiz({
      selected_notes: selectedNotes.value,
      selected_files: selectedFiles.value,
    })
    if (res.code !== 200 || !res.data?.questions?.length) {
      throw new Error(res.message || '生成失败')
    }
    quiz.value = res.data
    userAnswers.value = {}
    score.value = 0
    step.value = 'quiz'
  } catch (error) {
    errorMessage.value = messageFromError(error, '测试生成失败')
    step.value = 'selection'
  } finally {
    stopGeneratingMessages()
  }
}

function handleSubmitQuiz() {
  if (!quiz.value) return
  const unanswered = quiz.value.questions.filter((q) => !userAnswers.value[q.id])
  if (unanswered.length) {
    errorMessage.value = `还有 ${unanswered.length} 道题未回答`
    return
  }

  errorMessage.value = ''
  score.value = quiz.value.questions.reduce((total, question) => (
    total + (userAnswers.value[question.id] === question.answer ? 1 : 0)
  ), 0)
  step.value = 'result'
}

function toggleNote(noteId: string) {
  selectedNotes.value = selectedNotes.value.includes(noteId)
    ? selectedNotes.value.filter((id) => id !== noteId)
    : [...selectedNotes.value, noteId]
}

function toggleFile(docId: string) {
  selectedFiles.value = selectedFiles.value.includes(docId)
    ? selectedFiles.value.filter((id) => id !== docId)
    : [...selectedFiles.value, docId]
}

function toggleAllNotes() {
  selectedNotes.value = toggleVisibleSelection(selectedNotes.value, visibleNoteIds.value, allNotesSelected.value)
}

function toggleAllDocs() {
  selectedFiles.value = toggleVisibleSelection(selectedFiles.value, visibleDocumentIds.value, allDocsSelected.value)
}

function toggleVisibleSelection(selectedIds: string[], visibleIds: string[], allVisibleSelected: boolean) {
  const visibleSet = new Set(visibleIds)
  if (allVisibleSelected) {
    return selectedIds.filter((id) => !visibleSet.has(id))
  }
  return Array.from(new Set([...selectedIds, ...visibleIds]))
}

function isNoteFolderCollapsed(key: string) {
  if (noteSearch.value.trim()) return false
  return !collapsedNoteFolderKeys.value.has(key)
}

function isDocumentFolderCollapsed(key: string) {
  if (fileSearch.value.trim()) return false
  return !collapsedDocumentFolderKeys.value.has(key)
}

function toggleNoteFolder(key: string) {
  collapsedNoteFolderKeys.value = toggleCollapsedSet(collapsedNoteFolderKeys.value, key)
}

function toggleDocumentFolder(key: string) {
  collapsedDocumentFolderKeys.value = toggleCollapsedSet(collapsedDocumentFolderKeys.value, key)
}

function toggleCollapsedSet(current: Set<string>, key: string) {
  const next = new Set(current)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  return next
}

function docTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.filename || doc.title || '未命名文档'
}

function formatDate(value?: string | null) {
  if (!value) return '未更新'
  return new Date(value).toLocaleDateString()
}

function formatFileSize(value?: number) {
  if (!value) return '未知大小'
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function messageFromError(error: unknown, fallback: string) {
  const maybeError = error as { response?: { data?: { detail?: string; message?: string } }; message?: string }
  return maybeError.response?.data?.detail || maybeError.response?.data?.message || maybeError.message || fallback
}

function optionClass(questionId: string, option: string) {
  const selected = userAnswers.value[questionId] === option
  return selected
    ? 'border-[var(--color-accent)] bg-[var(--color-accent-bg)] text-[var(--color-accent)] font-medium'
    : 'border-[var(--color-border)] bg-[var(--color-card)] text-[var(--color-text-secondary)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)]'
}

function resultOptionClass(questionId: string, option: string, answer: string) {
  const selected = userAnswers.value[questionId] === option
  if (option === answer) {
    return 'border-[var(--color-success)] bg-[var(--color-success-bg)] text-[var(--color-success)] font-medium'
  }
  if (selected && option !== answer) {
    return 'border-[var(--color-danger)] bg-[var(--color-danger-bg)] text-[var(--color-danger)] font-medium'
  }
  return 'border-[var(--color-border)] bg-[var(--color-card)] text-[var(--color-text-secondary)] opacity-70'
}

function resetToSelection() {
  quiz.value = null
  userAnswers.value = {}
  score.value = 0
  errorMessage.value = ''
  step.value = 'selection'
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="mx-auto flex min-h-[calc(100vh-8rem)] max-w-6xl flex-col gap-5">
    <div v-if="errorMessage" class="rounded-md border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger)]">
      {{ errorMessage }}
    </div>

    <section v-if="step === 'selection'" class="flex flex-1 flex-col gap-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <Brain class="text-[var(--color-accent)]" :size="24" />
          <h2 class="font-heading text-2xl font-semibold">快速测试</h2>
        </div>
        <button
          class="inline-flex items-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
          type="button"
          @click="loadData"
        >
          <RotateCcw :size="16" />
          刷新
        </button>
      </div>

      <div v-if="loadingContext" class="flex flex-1 flex-col items-center justify-center gap-3 py-20 text-sm text-[var(--color-text-secondary)]">
        <Loader2 class="animate-spin text-[var(--color-accent)]" :size="36" />
        正在加载可选内容
      </div>

      <div v-else class="grid flex-1 gap-5 lg:grid-cols-2">
        <div class="flex min-h-[32rem] flex-col overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
          <div class="flex items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3">
            <div class="flex items-center gap-2 text-sm font-medium">
              <FileText class="text-[var(--color-success)]" :size="17" />
              <span>笔记 {{ selectedNotes.length }}/{{ notes.length }}</span>
            </div>
            <button class="text-xs text-[var(--color-accent)] hover:underline disabled:opacity-50" type="button" :disabled="visibleNoteIds.length === 0" @click="toggleAllNotes">
              {{ allNotesSelected ? '取消全选' : '全选' }}
            </button>
          </div>
          <div class="border-b border-[var(--color-border)] p-3">
            <label class="relative block">
              <Search class="absolute left-3 top-2.5 text-[var(--color-text-tertiary)]" :size="16" />
              <input v-model="noteSearch" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] py-2 pl-9 pr-3 text-sm outline-none focus:border-[var(--color-accent)]" placeholder="搜索笔记" />
            </label>
          </div>
          <div class="flex-1 overflow-y-auto p-3">
            <div
              v-for="row in noteRows"
              :key="row.key"
              class="mb-1 last:mb-0"
            >
              <p v-if="row.kind === 'empty'" class="py-10 text-center text-sm text-[var(--color-text-tertiary)]">{{ row.title }}</p>
              <button
                v-else-if="row.kind === 'folder'"
                class="flex min-h-9 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
                type="button"
                :aria-expanded="!isNoteFolderCollapsed(row.key)"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="toggleNoteFolder(row.key)"
              >
                <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform" :class="{ 'rotate-90': !isNoteFolderCollapsed(row.key) }" />
                <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </button>
              <button
                v-else
                class="flex min-h-12 w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-bg-secondary)]"
                :class="row.sourceId && selectedNotes.includes(row.sourceId) ? 'border-[var(--color-success)] bg-[var(--color-success-bg)]' : 'border-transparent'"
                type="button"
                :aria-pressed="row.sourceId ? selectedNotes.includes(row.sourceId) : false"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="row.sourceId && toggleNote(row.sourceId)"
              >
                <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-[var(--color-border)]" :class="{ 'bg-[var(--color-success)] text-white': row.sourceId && selectedNotes.includes(row.sourceId) }">
                  <Check v-if="row.sourceId && selectedNotes.includes(row.sourceId)" :size="14" />
                </span>
                <FileText :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium">{{ row.title }}</span>
                  <span v-if="row.subtitle" class="mt-1 block truncate text-xs text-[var(--color-text-tertiary)]">{{ row.subtitle }}</span>
                </span>
              </button>
            </div>
          </div>
        </div>

        <div class="flex min-h-[32rem] flex-col overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-card)]">
          <div class="flex items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-3">
            <div class="flex items-center gap-2 text-sm font-medium">
              <Database class="text-[var(--color-accent)]" :size="17" />
              <span>知识库 {{ selectedFiles.length }}/{{ documents.length }}</span>
            </div>
            <button class="text-xs text-[var(--color-accent)] hover:underline disabled:opacity-50" type="button" :disabled="visibleDocumentIds.length === 0" @click="toggleAllDocs">
              {{ allDocsSelected ? '取消全选' : '全选' }}
            </button>
          </div>
          <div class="border-b border-[var(--color-border)] p-3">
            <label class="relative block">
              <Search class="absolute left-3 top-2.5 text-[var(--color-text-tertiary)]" :size="16" />
              <input v-model="fileSearch" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] py-2 pl-9 pr-3 text-sm outline-none focus:border-[var(--color-accent)]" placeholder="搜索知识库文档" />
            </label>
          </div>
          <div class="flex-1 overflow-y-auto p-3">
            <div
              v-for="row in documentRows"
              :key="row.key"
              class="mb-1 last:mb-0"
            >
              <p v-if="row.kind === 'empty'" class="py-10 text-center text-sm text-[var(--color-text-tertiary)]">{{ row.title }}</p>
              <button
                v-else-if="row.kind === 'folder'"
                class="flex min-h-9 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
                type="button"
                :aria-expanded="!isDocumentFolderCollapsed(row.key)"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="toggleDocumentFolder(row.key)"
              >
                <ChevronRight :size="14" class="shrink-0 text-[var(--color-text-tertiary)] transition-transform" :class="{ 'rotate-90': !isDocumentFolderCollapsed(row.key) }" />
                <Folder :size="15" class="shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1 truncate font-medium">{{ row.title }}</span>
                <span class="shrink-0 text-xs text-[var(--color-text-tertiary)]">{{ row.count }}</span>
              </button>
              <button
                v-else
                class="flex min-h-12 w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-bg-secondary)]"
                :class="row.sourceId && selectedFiles.includes(row.sourceId) ? 'border-[var(--color-accent)] bg-[var(--color-accent-bg)]' : 'border-transparent'"
                type="button"
                :aria-pressed="row.sourceId ? selectedFiles.includes(row.sourceId) : false"
                :style="{ paddingLeft: `${0.75 + row.depth * 0.875}rem` }"
                @click="row.sourceId && toggleFile(row.sourceId)"
              >
                <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-[var(--color-border)]" :class="{ 'bg-[var(--color-accent)] text-white': row.sourceId && selectedFiles.includes(row.sourceId) }">
                  <Check v-if="row.sourceId && selectedFiles.includes(row.sourceId)" :size="14" />
                </span>
                <Database :size="15" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium">{{ row.title }}</span>
                  <span v-if="row.subtitle" class="mt-1 block truncate text-xs text-[var(--color-text-tertiary)]">{{ row.subtitle }}</span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-center">
        <button
          class="inline-flex items-center gap-2 rounded-md bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="selectedNotes.length === 0 && selectedFiles.length === 0"
          @click="handleGenerate"
        >
          <Sparkles :size="17" />
          AI 智能生成测验
        </button>
      </div>
    </section>

    <section v-else-if="step === 'generating'" class="flex flex-1 flex-col items-center justify-center gap-7 py-20">
      <div class="relative flex h-28 w-28 items-center justify-center">
        <div class="absolute h-28 w-28 animate-ping rounded-full border border-[var(--color-accent)] opacity-20" />
        <div class="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-accent)] text-white shadow-lg">
          <Brain :size="32" />
        </div>
      </div>
      <div class="text-center">
        <h2 class="font-heading text-lg font-semibold">AI 快速测验生成中</h2>
        <p class="mt-2 text-sm text-[var(--color-text-secondary)]">{{ generatingMessage }}</p>
      </div>
    </section>

    <section v-else-if="step === 'quiz' && quiz" class="flex flex-1 flex-col gap-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <button class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="resetToSelection">
            <ArrowLeft :size="18" />
          </button>
          <div>
            <h2 class="font-heading text-xl font-semibold">{{ quiz.title }}</h2>
            <p v-if="quiz.description" class="mt-1 text-sm text-[var(--color-text-secondary)]">{{ quiz.description }}</p>
          </div>
        </div>
        <span class="text-sm text-[var(--color-text-secondary)]">{{ answeredCount }}/{{ quiz.questions.length }}</span>
      </div>

      <div class="space-y-4">
        <article v-for="(question, index) in quiz.questions" :key="question.id" class="space-y-4 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-5">
          <div>
            <span class="inline-flex rounded-full bg-[var(--color-bg-secondary)] px-2.5 py-1 text-xs text-[var(--color-text-secondary)]">
              问题 {{ index + 1 }} / {{ quiz.questions.length }} · {{ question.type === 'true_false' ? '判断题' : '单选题' }}
            </span>
            <h3 class="mt-3 text-base font-semibold leading-7">{{ question.question }}</h3>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <button
              v-for="option in question.options"
              :key="option"
              class="flex min-h-12 items-center justify-between rounded-md border px-4 py-3 text-left text-sm transition-colors"
              :class="optionClass(question.id, option)"
              type="button"
              @click="userAnswers = { ...userAnswers, [question.id]: option }"
            >
              <span>{{ option }}</span>
              <Check v-if="userAnswers[question.id] === option" class="ml-3 shrink-0" :size="16" />
            </button>
          </div>
        </article>
      </div>

      <div class="flex justify-center pb-8">
        <button class="inline-flex items-center gap-2 rounded-md bg-[var(--color-accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700" type="button" @click="handleSubmitQuiz">
          <Play :size="17" />
          提交测验
        </button>
      </div>
    </section>

    <section v-else-if="step === 'result' && quiz" class="flex flex-1 flex-col gap-5">
      <div class="flex flex-wrap items-center justify-between gap-5 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] p-5">
        <div>
          <h2 class="font-heading text-xl font-semibold">测验结果</h2>
          <p class="mt-2 text-sm text-[var(--color-text-secondary)]">得分 {{ score }} / {{ quiz.questions.length }}</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button class="inline-flex items-center gap-2 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="step = 'quiz'; userAnswers = {}">
              <RotateCcw :size="15" />
              重新答题
            </button>
            <button class="inline-flex items-center gap-2 rounded-md bg-[var(--color-accent)] px-3 py-2 text-sm font-medium text-white hover:bg-blue-700" type="button" @click="resetToSelection">
              <Sparkles :size="15" />
              重新出题
            </button>
          </div>
        </div>
        <div class="relative flex h-24 w-24 shrink-0 items-center justify-center">
          <svg class="h-24 w-24 -rotate-90">
            <circle cx="48" cy="48" r="39" class="fill-transparent stroke-[var(--color-border)]" stroke-width="8" />
            <circle
              cx="48"
              cy="48"
              r="39"
              class="fill-transparent stroke-[var(--color-accent)] transition-all"
              stroke-width="8"
              stroke-linecap="round"
              :stroke-dasharray="245"
              :stroke-dashoffset="245 - (245 * score) / quiz.questions.length"
            />
          </svg>
          <span class="absolute text-xl font-semibold">{{ Math.round((score / quiz.questions.length) * 100) }}%</span>
        </div>
      </div>

      <div class="space-y-4">
        <article v-for="(question, index) in quiz.questions" :key="question.id" class="space-y-4 rounded-md border bg-[var(--color-card)] p-5" :class="userAnswers[question.id] === question.answer ? 'border-[var(--color-success)]' : 'border-[var(--color-danger)]'">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <div class="mb-2 flex flex-wrap gap-2">
                <span class="rounded-full bg-[var(--color-bg-secondary)] px-2.5 py-1 text-xs text-[var(--color-text-secondary)]">问题 {{ index + 1 }}</span>
                <span v-if="userAnswers[question.id] === question.answer" class="inline-flex items-center gap-1 rounded-full bg-[var(--color-success-bg)] px-2.5 py-1 text-xs text-[var(--color-success)]">
                  <CheckCircle2 :size="12" />
                  回答正确
                </span>
                <span v-else class="inline-flex items-center gap-1 rounded-full bg-[var(--color-danger-bg)] px-2.5 py-1 text-xs text-[var(--color-danger)]">
                  <XCircle :size="12" />
                  回答错误
                </span>
              </div>
              <h3 class="text-base font-semibold leading-7">{{ question.question }}</h3>
            </div>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <div
              v-for="option in question.options"
              :key="option"
              class="flex min-h-12 items-center justify-between rounded-md border px-4 py-3 text-left text-sm"
              :class="resultOptionClass(question.id, option, question.answer)"
            >
              <span>{{ option }}</span>
              <CheckCircle2 v-if="option === question.answer" class="ml-3 shrink-0 text-[var(--color-success)]" :size="16" />
              <XCircle v-else-if="userAnswers[question.id] === option" class="ml-3 shrink-0 text-[var(--color-danger)]" :size="16" />
            </div>
          </div>

          <div v-if="question.explanation" class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4">
            <div class="mb-2 flex items-center gap-2 text-sm font-medium text-[var(--color-accent)]">
              <Info :size="15" />
              AI 智能解析
            </div>
            <p class="text-sm leading-6 text-[var(--color-text-secondary)]">{{ question.explanation }}</p>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
