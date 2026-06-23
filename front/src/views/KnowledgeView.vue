<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  Search,
  Settings2,
  Tag,
  Trash2,
  Upload,
} from '@lucide/vue'
import CategoryManageDialog from '../components/CategoryManageDialog.vue'
import { knowledgeApi } from '../api/knowledge'
import type { KnowledgeDocument, KnowledgeFolder } from '../types/api'

type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

type FolderMode = 'all' | 'unfiled' | 'folder'

interface FolderRow {
  folder: KnowledgeFolder
  depth: number
}

interface FolderOption {
  id: string
  name: string
  depth: number
  folder: KnowledgeFolder
}

const router = useRouter()

const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const uploading = ref(false)
const deletingId = ref('')
const searchQuery = ref('')
const category = ref('')
const message = ref('')
const errorMessage = ref('')
const folderError = ref('')
const progressMessage = ref('')
const progressValue = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const folders = ref<KnowledgeFolder[]>([])
const totalDocumentCount = ref(0)
const unfiledCount = ref(0)
const activeFolderMode = ref<FolderMode>('all')
const activeFolderId = ref<string | null>(null)
const expandedFolderIds = ref<Set<string>>(new Set())

const folderDialogOpen = ref(false)
const folderDialogMode = ref<'create' | 'edit'>('create')
const folderFormName = ref('')
const folderFormParentId = ref<string | null>(null)
const editingFolder = ref<KnowledgeFolder | null>(null)
const deleteFolderTarget = ref<KnowledgeFolder | null>(null)
const movingFolder = ref(false)
const manageOpen = ref(false)
const extraCategories = ref<string[]>([])
const categoryCounts = ref<Record<string, number>>({})

const acceptTypes = '.pdf,.txt,.md,.markdown,.doc,.docx,.ppt,.pptx,application/pdf,text/plain,text/markdown,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation'

const PREDEFINED_CATEGORIES = [
  { label: '全部', value: '' },
  { label: '工作', value: 'work' },
  { label: '学习', value: 'study' },
  { label: '生活', value: 'life' },
  { label: '技术', value: 'project' },
  { label: '其他', value: 'other' },
]
const PREDEFINED_VALUES = new Set(['work', 'study', 'life', 'project', 'other'])
const CATEGORY_ORDER_KEY = 'knowledge_category_order'

const typeLabels: Record<string, string> = {
  'ai-summary': 'AI总结',
  pdf: 'PDF',
  markdown: 'Markdown',
  word: 'Word',
  presentation: 'PPT',
  text: '文本',
  document: '文档',
}

const allCategories = ref(PREDEFINED_CATEGORIES)

const folderNameById = computed(() => {
  const map = new Map<string, string>()
  const walk = (nodes: KnowledgeFolder[]) => {
    for (const node of nodes) {
      map.set(node.id, node.name)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(folders.value)
  return map
})

const folderOptions = computed<FolderOption[]>(() => flattenFolders(folders.value, false))
const visibleFolderRows = computed<FolderRow[]>(() => flattenFolders(folders.value, true))
const activeFolderTitle = computed(() => {
  if (activeFolderMode.value === 'unfiled') return '未归档'
  if (activeFolderMode.value === 'folder') return folderName(activeFolderId.value) || '文件夹'
  return '全部文档'
})
const activeFolderSelect = computed({
  get() {
    if (activeFolderMode.value === 'folder' && activeFolderId.value) return `folder:${activeFolderId.value}`
    return activeFolderMode.value
  },
  set(value: string) {
    if (value === 'all') {
      selectFolder('all')
    } else if (value === 'unfiled') {
      selectFolder('unfiled')
    } else if (value.startsWith('folder:')) {
      selectFolder('folder', value.slice(7))
    }
  },
})
const parentOptions = computed(() => {
  if (!editingFolder.value) return folderOptions.value
  const blocked = new Set(descendantIds(editingFolder.value))
  blocked.add(editingFolder.value.id)
  return folderOptions.value.filter((item) => !blocked.has(item.id))
})

function flattenFolders(items: KnowledgeFolder[], visibleOnly: boolean, depth = 0): FolderOption[] {
  const rows: FolderOption[] = []
  for (const folder of items) {
    rows.push({ id: folder.id, name: folder.name, depth, folder })
    if (!visibleOnly || expandedFolderIds.value.has(folder.id)) {
      rows.push(...flattenFolders(folder.children || [], visibleOnly, depth + 1))
    }
  }
  return rows
}

function descendantIds(folder: KnowledgeFolder): string[] {
  const ids: string[] = []
  for (const child of folder.children || []) {
    ids.push(child.id, ...descendantIds(child))
  }
  return ids
}

function getErrorMessage(error: unknown, fallback: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallback
}

function getDocumentTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.title || doc.filename
}

function getExtension(doc: KnowledgeDocument) {
  const explicitExt = doc.file_ext?.trim().toLowerCase()
  if (explicitExt) return explicitExt.startsWith('.') ? explicitExt : `.${explicitExt}`
  const match = getDocumentTitle(doc).match(/\.[^.]+$/)
  return match?.[0].toLowerCase() || ''
}

function normalizeText(value?: string | null) {
  return (value || '').toLowerCase().replace(/\s+/g, '')
}

function normalizePreview(value?: string | null) {
  return (value || '').replace(/\s+/g, ' ').trim()
}

function isSubsequence(needle: string, haystack: string) {
  if (!needle) return true
  let index = 0
  for (const char of haystack) {
    if (char === needle[index]) {
      index += 1
      if (index === needle.length) return true
    }
  }
  return false
}

function isAiSummaryDocument(doc: KnowledgeDocument) {
  const corpus = normalizeText([
    doc.title,
    doc.filename,
    doc.original_filename,
    doc.preview,
    doc.status_message,
  ].filter(Boolean).join(' '))
  return corpus.includes('ai总结') || corpus.includes('aisummary') || corpus.includes('summary') || corpus.includes('总结')
}

function getDocumentType(doc: KnowledgeDocument) {
  if (isAiSummaryDocument(doc)) return 'ai-summary'
  const ext = getExtension(doc)
  if (ext === '.pdf' || doc.mime_type === 'application/pdf') return 'pdf'
  if (ext === '.md' || ext === '.markdown' || doc.mime_type === 'text/markdown') return 'markdown'
  if (ext === '.txt' || doc.mime_type === 'text/plain') return 'text'
  if (ext === '.doc' || ext === '.docx') return 'word'
  if (ext === '.ppt' || ext === '.pptx') return 'presentation'
  return 'document'
}

function getDocumentTypeLabel(doc: KnowledgeDocument) {
  return typeLabels[getDocumentType(doc)] || '文档'
}

function getDocumentPreview(doc: KnowledgeDocument) {
  const preview = normalizePreview(doc.preview)
  if (preview) return preview
  if (doc.status === 'failed' && doc.status_message) return doc.status_message
  if (doc.status && doc.status !== 'ready') return doc.status === 'pending' ? '正在处理文档，完成后可进入预览。' : doc.status
  return '暂无预览内容'
}

function formatDate(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function folderName(folderId: string | null | undefined) {
  if (!folderId) return ''
  return folderNameById.value.get(folderId) || folderOptions.value.find((item) => item.id === folderId)?.name || `文件夹（${folderId.slice(0, 6)}）`
}

function folderOptionLabel(item: FolderOption) {
  const prefix = '-- '.repeat(item.depth)
  const name = item.name || `文件夹（${item.id.slice(0, 6)}）`
  return `${prefix}${name}`
}

function categoryLabel(value: string | null | undefined) {
  if (!value) return ''
  return allCategories.value.find((item) => item.value === value)?.label || value
}

function getSavedOrder(): string[] {
  try {
    const raw = localStorage.getItem(CATEGORY_ORDER_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function buildCategoryList(customCategories: string[]) {
  const list = PREDEFINED_CATEGORIES.slice()
  for (const item of customCategories) {
    if (item && !PREDEFINED_VALUES.has(item)) {
      list.push({ label: item, value: item })
    }
  }

  const order = getSavedOrder()
  if (order.length === 0) return list
  const orderIndex = new Map(order.map((value, index) => [value, index]))

  return list.sort((a, b) => {
    if (a.value === '') return -1
    if (b.value === '') return 1
    const aIndex = orderIndex.get(a.value)
    const bIndex = orderIndex.get(b.value)
    if (aIndex !== undefined && bIndex !== undefined) return aIndex - bIndex
    if (aIndex !== undefined) return -1
    if (bIndex !== undefined) return 1
    return 0
  })
}

function matchesQuery(doc: KnowledgeDocument) {
  const compactQuery = normalizeText(searchQuery.value)
  if (!compactQuery) return true
  const corpus = normalizeText([
    getDocumentTitle(doc),
    doc.filename,
    doc.preview,
    doc.status_message,
    doc.category,
    ...(doc.tags || []),
    getDocumentTypeLabel(doc),
    getExtension(doc),
    folderName(doc.folder_id),
  ].filter(Boolean).join(' '))
  return corpus.includes(compactQuery) || isSubsequence(compactQuery, corpus)
}

const filteredDocuments = computed(() => documents.value.filter((doc) => matchesQuery(doc)))
const documentCount = computed(() => filteredDocuments.value.length)

function folderFilterParams() {
  if (activeFolderMode.value === 'folder' && activeFolderId.value) {
    const exists = folderOptions.value.some((item) => item.id === activeFolderId.value)
    if (!exists) {
      activeFolderMode.value = 'all'
      activeFolderId.value = null
      return {}
    }
    return { folder_id: activeFolderId.value }
  }
  if (activeFolderMode.value === 'unfiled') return { unfiled: true }
  return {}
}

async function refreshCategories(extra = extraCategories.value) {
  try {
    const res = await knowledgeApi.stats()
    const statsCats = res.data.categories ?? []
    const counts: Record<string, number> = {}
    for (const item of statsCats) {
      counts[item.category] = item.count
    }
    categoryCounts.value = counts
    const all = [...new Set([...statsCats.map((item) => item.category), ...extra])]
    allCategories.value = buildCategoryList(all)
    if (category.value && !allCategories.value.some((item) => item.value === category.value)) {
      category.value = ''
    }
  } catch {
    allCategories.value = buildCategoryList(extra)
  }
}

async function loadFolders() {
  folderError.value = ''
  try {
    const res = await knowledgeApi.listFolders()
    folders.value = res.data.folders || []
    totalDocumentCount.value = res.data.total_count || 0
    unfiledCount.value = res.data.unfiled_count || 0
    const known = new Set(folderOptions.value.map((item) => item.id))
    if (activeFolderMode.value === 'folder' && activeFolderId.value && !known.has(activeFolderId.value)) {
      selectFolder('all')
    }
  } catch (error) {
    folders.value = []
    folderError.value = getErrorMessage(error, '文件夹加载失败')
  }
}

async function load() {
  loading.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const res = await knowledgeApi.list({
      ...folderFilterParams(),
      category: category.value || undefined,
    })
    documents.value = res.data.documents || []
  } catch (error) {
    documents.value = []
    errorMessage.value = getErrorMessage(error, '文档加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await loadFolders()
  await refreshCategories()
  await load()
}

function resetAndLoad() {
  void load()
}

function selectFolder(mode: FolderMode, folderId: string | null = null) {
  activeFolderMode.value = mode
  activeFolderId.value = mode === 'folder' ? folderId : null
  resetAndLoad()
}

function toggleFolder(folderId: string) {
  const next = new Set(expandedFolderIds.value)
  if (next.has(folderId)) next.delete(folderId)
  else next.add(folderId)
  expandedFolderIds.value = next
}

function openCreateFolder(parentId: string | null = null) {
  folderDialogMode.value = 'create'
  editingFolder.value = null
  folderFormName.value = ''
  folderFormParentId.value = parentId
  folderDialogOpen.value = true
}

function openEditFolder(folder: KnowledgeFolder) {
  folderDialogMode.value = 'edit'
  editingFolder.value = folder
  folderFormName.value = folder.name
  folderFormParentId.value = folder.parent_id
  folderDialogOpen.value = true
}

async function saveFolder() {
  const name = folderFormName.value.trim()
  if (!name || movingFolder.value) return
  movingFolder.value = true
  errorMessage.value = ''
  try {
    if (folderDialogMode.value === 'edit' && editingFolder.value) {
      await knowledgeApi.updateFolder(editingFolder.value.id, {
        name,
        parent_id: folderFormParentId.value || null,
      })
    } else {
      await knowledgeApi.createFolder({
        name,
        parent_id: folderFormParentId.value || null,
      })
    }
    folderDialogOpen.value = false
    await refreshAll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '文件夹保存失败')
  } finally {
    movingFolder.value = false
  }
}

async function deleteFolder(mode: 'unfile' | 'delete_documents') {
  const target = deleteFolderTarget.value
  if (!target) return
  try {
    await knowledgeApi.deleteFolder(target.id, mode)
    const removed = new Set([target.id, ...descendantIds(target)])
    if (activeFolderId.value && removed.has(activeFolderId.value)) {
      activeFolderMode.value = 'all'
      activeFolderId.value = null
    }
    deleteFolderTarget.value = null
    await refreshAll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '文件夹删除失败')
  }
}

function openFilePicker() {
  if (!uploading.value) fileInput.value?.click()
}

function currentFolderIdForUpload(): string | null {
  return activeFolderMode.value === 'folder' ? activeFolderId.value : null
}

async function uploadFiles(fileList: FileList | File[]) {
  const files = Array.from(fileList)
  if (!files.length || uploading.value) return

  uploading.value = true
  message.value = ''
  errorMessage.value = ''
    progressMessage.value = '正在上传文件...'
    progressValue.value = 0
  try {
    const result = await knowledgeApi.uploadMultiple(files, currentFolderIdForUpload(), category.value || undefined)
    const finalEvent = result.finalEvent
    const successCount = finalEvent?.success_count ?? files.length
    const failedCount = finalEvent?.failed_count ?? 0
    progressValue.value = finalEvent?.progress ?? 100
    message.value = failedCount > 0 ? `已完成 ${successCount} 个文档，失败 ${failedCount} 个` : `已上传 ${successCount} 个文档`
    if (failedCount > 0 && result.lastError) errorMessage.value = result.lastError
    await refreshAll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '上传失败，请确认文件格式和大小后重试')
  } finally {
    uploading.value = false
    progressMessage.value = ''
  }
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) await uploadFiles(input.files)
  input.value = ''
}

function openDocument(documentId: string) {
  void router.push(`/knowledge/${documentId}`)
}

async function deleteDocument(doc: KnowledgeDocument) {
  if (deletingId.value) return
  const filename = getDocumentTitle(doc)
  const confirmed = window.confirm(`确认删除「${filename}」？删除后会从知识库检索中移除。`)
  if (!confirmed) return

  deletingId.value = doc.id
  message.value = ''
  errorMessage.value = ''
  try {
    await knowledgeApi.delete(doc.id)
    await refreshAll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除文档失败，请稍后重试')
  } finally {
    deletingId.value = ''
  }
}

function createCategory(name: string) {
  if (!extraCategories.value.includes(name)) {
    extraCategories.value = [...extraCategories.value, name]
  }
}

onMounted(() => {
  void refreshAll()
})

watch(category, () => {
  resetAndLoad()
})

watch(extraCategories, () => {
  void refreshCategories()
}, { deep: true })
</script>

<template>
  <div class="mx-auto flex h-[calc(100vh-7rem)] max-w-6xl gap-4 overflow-hidden px-1 py-2">
    <input
      ref="fileInput"
      class="sr-only"
      type="file"
      multiple
      :accept="acceptTypes"
      @change="handleFileChange"
    />

    <aside class="hidden w-72 shrink-0 flex-col border-r border-[var(--color-border-light)] pr-4 md:flex">
      <div class="mb-4 flex items-center justify-between gap-2">
        <span class="text-base font-medium text-[var(--color-text)]">文件夹</span>
        <button class="rounded-md p-2 text-[var(--color-text-tertiary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)]" type="button" title="新建文件夹" @click="openCreateFolder()">
          <FolderPlus :size="20" />
        </button>
      </div>
      <button
        class="mb-1.5 flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left text-sm transition-colors"
        :class="activeFolderMode === 'all' ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]'"
        type="button"
        @click="selectFolder('all')"
      >
        <span class="inline-flex min-w-0 items-center gap-2.5">
          <FileText :size="18" />
          <span class="truncate">全部文档</span>
        </span>
        <span>{{ totalDocumentCount }}</span>
      </button>
      <button
        class="mb-3 flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left text-sm transition-colors"
        :class="activeFolderMode === 'unfiled' ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]'"
        type="button"
        @click="selectFolder('unfiled')"
      >
        <span class="inline-flex min-w-0 items-center gap-2.5">
          <FolderOpen v-if="activeFolderMode === 'unfiled'" :size="18" />
          <Folder v-else :size="18" />
          <span class="truncate">未归档</span>
        </span>
        <span>{{ unfiledCount }}</span>
      </button>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <p v-if="folderError" class="mb-2 text-sm text-[var(--color-danger)]">{{ folderError }}</p>
        <p v-if="visibleFolderRows.length === 0" class="py-4 text-sm text-[var(--color-text-tertiary)]">暂无文件夹</p>
        <div v-for="row in visibleFolderRows" :key="row.folder.id" class="group flex items-center gap-1.5">
          <button
            class="flex min-w-0 flex-1 items-center justify-between rounded-md py-2.5 pr-2.5 text-left text-sm transition-colors"
            :class="activeFolderMode === 'folder' && activeFolderId === row.folder.id ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]'"
            :style="{ paddingLeft: `${10 + row.depth * 18}px` }"
            type="button"
            @click="selectFolder('folder', row.folder.id)"
          >
            <span class="inline-flex min-w-0 items-center gap-2">
              <button v-if="row.folder.children.length" class="rounded p-1 hover:bg-[var(--color-bg-tertiary)]" type="button" @click.stop="toggleFolder(row.folder.id)">
                <ChevronDown v-if="expandedFolderIds.has(row.folder.id)" :size="15" />
                <ChevronRight v-else :size="15" />
              </button>
              <span v-else class="w-[23px] shrink-0" />
              <FolderOpen v-if="activeFolderMode === 'folder' && activeFolderId === row.folder.id" :size="18" />
              <Folder v-else :size="18" />
              <span class="truncate">{{ row.folder.name }}</span>
            </span>
            <span class="ml-2 shrink-0">{{ row.folder.knowledge_count }}</span>
          </button>
          <button class="rounded p-1.5 text-[var(--color-text-tertiary)] opacity-0 hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)] group-hover:opacity-100" type="button" title="新建子文件夹" @click="openCreateFolder(row.folder.id)">
            <FolderPlus :size="16" />
          </button>
          <button class="rounded p-1.5 text-[var(--color-text-tertiary)] opacity-0 hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text)] group-hover:opacity-100" type="button" title="编辑文件夹" @click="openEditFolder(row.folder)">
            <Settings2 :size="16" />
          </button>
          <button class="rounded p-1.5 text-[var(--color-text-tertiary)] opacity-0 hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] group-hover:opacity-100" type="button" title="删除文件夹" @click="deleteFolderTarget = row.folder">
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <section class="shrink-0 border-b border-[var(--color-border-light)] bg-[var(--color-bg)] pb-4">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="text-sm text-[var(--color-text-secondary)]">
            {{ `${activeFolderTitle} · 共 ${documentCount} 篇` }}
          </div>
          <div class="flex items-center gap-2">
            <button class="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--color-border)] px-3 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed disabled:opacity-60" type="button" :disabled="uploading" @click="openFilePicker">
              <Upload :size="15" />
              {{ uploading ? '导入中' : '导入' }}
            </button>
          </div>
        </div>

        <div class="mb-4 flex flex-wrap gap-3">
          <select v-model="activeFolderSelect" class="h-10 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-3 text-xs text-[var(--color-text)] outline-none md:hidden">
            <option value="all">全部文档</option>
            <option value="unfiled">未归档</option>
            <option v-for="item in folderOptions" :key="item.id" :value="`folder:${item.id}`">{{ folderOptionLabel(item) }}</option>
          </select>
          <form class="relative min-w-56 flex-1" @submit.prevent="resetAndLoad">
            <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-placeholder)]" />
            <input
              v-model="searchQuery"
              class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-2 pl-9 pr-4 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
              placeholder="搜索知识库"
            />
          </form>
          <button class="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="manageOpen = true">
            <Settings2 :size="14" />
            管理分类
          </button>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            v-for="item in allCategories"
            :key="item.value"
            class="rounded-md px-3 py-1.5 text-xs transition-colors"
            :class="category === item.value ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'"
            type="button"
            @click="category = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <div v-if="uploading || progressMessage" class="mt-3 space-y-2">
          <div class="h-2 overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
            <div
              class="h-full rounded-full bg-[var(--color-accent)] transition-all"
              :style="{ width: `${Math.max(4, Math.min(progressValue, 100))}%` }"
            />
          </div>
          <p class="text-sm text-[var(--color-text-secondary)]">{{ progressMessage || '正在处理文档...' }}</p>
        </div>
        <p v-if="message" class="mt-3 text-sm text-[var(--color-success)]">{{ message }}</p>
        <p v-if="errorMessage" class="mt-3 text-sm text-[var(--color-danger)]">{{ errorMessage }}</p>
      </section>

      <section class="min-h-0 flex-1 overflow-y-auto pr-2 pt-4">
        <div v-if="filteredDocuments.length === 0 && !loading" class="flex min-h-64 flex-col items-center justify-center rounded-md border border-dashed border-[var(--color-border)] bg-[var(--color-card)] p-8 text-center">
          <FileText :size="48" class="mb-3 text-[var(--color-text-tertiary)]" />
          <p class="mb-4 text-sm text-[var(--color-text-secondary)]">暂无文档</p>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm text-white" type="button" @click="openFilePicker">导入文档</button>
        </div>

        <div v-else class="grid gap-3">
          <article
            v-for="doc in filteredDocuments"
            :key="doc.id"
            class="cursor-pointer rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4 transition-colors hover:border-[var(--color-accent)]"
            @click="openDocument(doc.id)"
          >
            <div class="flex items-start gap-3">
              <FileText :size="18" class="mt-0.5 shrink-0 text-[var(--color-text-tertiary)]" />
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex items-start justify-between gap-3">
                  <h3 class="truncate text-sm font-medium text-[var(--color-text)]">{{ getDocumentTitle(doc) }}</h3>
                  <div class="flex shrink-0 items-center gap-1">
                    <span class="text-xs text-[var(--color-text-tertiary)]">{{ formatDate(doc.created_at) }}</span>
                    <button
                      class="rounded p-0.5 text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      :disabled="deletingId === doc.id"
                      title="删除文档"
                      @click.stop="deleteDocument(doc)"
                    >
                      <Trash2 :size="14" />
                    </button>
                  </div>
                </div>
                <p class="mb-2 line-clamp-2 text-xs text-[var(--color-text-secondary)]">{{ getDocumentPreview(doc) }}</p>
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="doc.folder_id" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Folder :size="10" />
                    {{ folderName(doc.folder_id) }}
                  </span>
                  <span v-if="doc.category" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Tag :size="10" />
                    {{ categoryLabel(doc.category) }}
                  </span>
                  <span class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ getDocumentTypeLabel(doc) }}</span>
                  <span v-for="tag in doc.tags || []" :key="tag" class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ tag }}</span>
                  <span class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Tag :size="10" />
                    {{ doc.chunk_count }} chunks
                  </span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div v-if="loading" class="flex justify-center py-4">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
        </div>
      </section>
    </div>

    <Teleport to="body">
      <div v-if="folderDialogOpen" class="fixed inset-0 z-50 bg-black/40" @click="folderDialogOpen = false" />
      <section v-if="folderDialogOpen" class="fixed left-1/2 top-1/2 z-50 w-[420px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
        <h3 class="mb-4 text-base font-medium text-[var(--color-text)]">{{ folderDialogMode === 'edit' ? '编辑文件夹' : '新建文件夹' }}</h3>
        <div class="space-y-3">
          <input v-model="folderFormName" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none" placeholder="文件夹名称" @keydown.enter="saveFolder" />
          <select v-model="folderFormParentId" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none">
            <option :value="null">根目录</option>
            <option v-for="item in parentOptions" :key="item.id" :value="item.id">{{ folderOptionLabel(item) }}</option>
          </select>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="folderDialogOpen = false">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white disabled:opacity-40" type="button" :disabled="!folderFormName.trim() || movingFolder" @click="saveFolder">{{ movingFolder ? '保存中' : '保存' }}</button>
        </div>
      </section>
    </Teleport>

    <Teleport to="body">
      <div v-if="deleteFolderTarget" class="fixed inset-0 z-50 bg-black/40" @click="deleteFolderTarget = null" />
      <section v-if="deleteFolderTarget" class="fixed left-1/2 top-1/2 z-50 w-[440px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
        <h3 class="mb-2 text-base font-medium text-[var(--color-text)]">删除文件夹</h3>
        <p class="mb-5 text-sm leading-relaxed text-[var(--color-text-secondary)]">删除「{{ deleteFolderTarget.name }}」时，可以将其中文档移回未归档，或同时删除该文件夹内的文档。</p>
        <div class="flex flex-wrap justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="deleteFolderTarget = null">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white" type="button" @click="deleteFolder('unfile')">移回未归档</button>
          <button class="rounded-md bg-red-500 px-4 py-1.5 text-sm text-white hover:bg-red-600" type="button" @click="deleteFolder('delete_documents')">同时删除文档</button>
        </div>
      </section>
    </Teleport>

    <CategoryManageDialog
      v-model:open="manageOpen"
      storage-key="knowledge_category_order"
      item-name="文档"
      :delete-category="knowledgeApi.deleteCategory"
      :categories="allCategories.filter((entry) => entry.value !== '').map((entry) => ({ category: entry.value, count: categoryCounts[entry.value] ?? 0 }))"
      @refresh="refreshCategories"
      @create-category="createCategory"
    />
  </div>
</template>
