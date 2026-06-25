<!--
模块职责：知识库列表界面，负责上传、分类、文件夹、批量操作和文档预览入口。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
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
  Pin,
  Search,
  Settings2,
  Tag,
  Trash2,
  Upload,
} from '@lucide/vue'
import CategoryManageDialog from '../components/CategoryManageDialog.vue'
import { knowledgeApi } from '../api/knowledge'
import { readJsonPref } from '../api/localPrefs'
import { confirmDialog } from '../composables/useAppDialog'
import type { KnowledgeDocument, KnowledgeFolder } from '../types/api'

/**
 * 类型：`ApiError` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type ApiError = {
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

/**
 * 类型：`FolderMode` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type FolderMode = 'all' | 'unfiled' | 'folder'

/**
 * 接口：`FolderRow` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface FolderRow {
  folder: KnowledgeFolder
  depth: number
}

/**
 * 接口：`FolderOption` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface FolderOption {
  id: string
  name: string
  depth: number
  folder: KnowledgeFolder
}

const router = useRouter()

const documents = ref<KnowledgeDocument[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const uploading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const deletingId = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const pinningId = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const searchQuery = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const category = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const message = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const errorMessage = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const folderError = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const progressMessage = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const progressValue = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

const folders = ref<KnowledgeFolder[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const totalDocumentCount = ref(0)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const unfiledCount = ref(0)
const activeFolderMode = ref<FolderMode>('all')
const activeFolderId = ref<string | null>(null)
const expandedFolderIds = ref<Set<string>>(new Set())

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const folderDialogOpen = ref(false)
const folderDialogMode = ref<'create' | 'edit'>('create')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const folderFormName = ref('')
const folderFormParentId = ref<string | null>(null)
const editingFolder = ref<KnowledgeFolder | null>(null)
const deleteFolderTarget = ref<KnowledgeFolder | null>(null)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const movingFolder = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
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

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const allCategories = ref(PREDEFINED_CATEGORIES)

/**
 * 用途：执行folderNameById相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const folderNameById = computed(() => {
  const map = new Map<string, string>()
  /**
   * 用途：执行walk相关业务逻辑。
   * @param nodes 调用方传入的nodes参数，用于驱动当前前端逻辑。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const walk = (nodes: KnowledgeFolder[]) => {
    for (const node of nodes) {
      map.set(node.id, node.name)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(folders.value)
  return map
})

/**
 * 用途：执行folderOptions相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const folderOptions = computed<FolderOption[]>(() => flattenFolders(folders.value, false))
/**
 * 用途：执行visibleFolderRows相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const visibleFolderRows = computed<FolderRow[]>(() => flattenFolders(folders.value, true))
/**
 * 用途：执行activeFolderTitle相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const activeFolderTitle = computed(() => {
  if (activeFolderMode.value === 'unfiled') return '未归档'
  if (activeFolderMode.value === 'folder') return folderName(activeFolderId.value) || '文件夹'
  return '全部文档'
})
// 派生状态：根据 props、store 或本地状态计算模板直接使用的数据。
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
/**
 * 用途：执行parentOptions相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const parentOptions = computed(() => {
  if (!editingFolder.value) return folderOptions.value
  const blocked = new Set(descendantIds(editingFolder.value))
  blocked.add(editingFolder.value.id)
  return folderOptions.value.filter((item) => !blocked.has(item.id))
})

/**
 * 用途：执行flattenFolders相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @param visibleOnly 调用方传入的visibleOnly参数，用于驱动当前前端逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行descendantIds相关业务逻辑。
 * @param folder 调用方传入的folder参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function descendantIds(folder: KnowledgeFolder): string[] {
  const ids: string[] = []
  for (const child of folder.children || []) {
    ids.push(child.id, ...descendantIds(child))
  }
  return ids
}

/**
 * 用途：执行getErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @param fallback 调用方传入的fallback参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getErrorMessage(error: unknown, fallback: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallback
}

/**
 * 用途：执行getDocumentTitle相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getDocumentTitle(doc: KnowledgeDocument) {
  return doc.original_filename || doc.title || doc.filename
}

/**
 * 用途：执行getExtension相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getExtension(doc: KnowledgeDocument) {
  const explicitExt = doc.file_ext?.trim().toLowerCase()
  if (explicitExt) return explicitExt.startsWith('.') ? explicitExt : `.${explicitExt}`
  const match = getDocumentTitle(doc).match(/\.[^.]+$/)
  return match?.[0].toLowerCase() || ''
}

/**
 * 用途：执行normalizeText相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function normalizeText(value?: string | null) {
  return (value || '').toLowerCase().replace(/\s+/g, '')
}

/**
 * 用途：执行normalizePreview相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function normalizePreview(value?: string | null) {
  return (value || '').replace(/\s+/g, ' ').trim()
}

/**
 * 用途：执行isSubsequence相关业务逻辑。
 * @param needle 调用方传入的needle参数，用于驱动当前前端逻辑。
 * @param haystack 调用方传入的haystack参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行isAiSummaryDocument相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行getDocumentType相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行getDocumentTypeLabel相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getDocumentTypeLabel(doc: KnowledgeDocument) {
  return typeLabels[getDocumentType(doc)] || '文档'
}

/**
 * 用途：执行getDocumentPreview相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getDocumentPreview(doc: KnowledgeDocument) {
  const preview = normalizePreview(doc.preview)
  if (preview) return preview
  if (doc.status === 'failed' && doc.status_message) return doc.status_message
  if (doc.status && doc.status !== 'ready') return doc.status === 'pending' ? '正在处理文档，完成后可进入预览。' : doc.status
  return '暂无预览内容'
}

/**
 * 用途：执行formatDate相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function formatDate(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/**
 * 用途：执行folderName相关业务逻辑。
 * @param folderId 调用方传入的folderId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderName(folderId: string | null | undefined) {
  if (!folderId) return ''
  return folderNameById.value.get(folderId) || folderOptions.value.find((item) => item.id === folderId)?.name || `文件夹（${folderId.slice(0, 6)}）`
}

/**
 * 用途：执行folderOptionLabel相关业务逻辑。
 * @param item 调用方传入的item参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderOptionLabel(item: FolderOption) {
  const prefix = '-- '.repeat(item.depth)
  const name = item.name || `文件夹（${item.id.slice(0, 6)}）`
  return `${prefix}${name}`
}

/**
 * 用途：执行categoryLabel相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function categoryLabel(value: string | null | undefined) {
  if (!value) return ''
  return allCategories.value.find((item) => item.value === value)?.label || value
}

/**
 * 用途：执行getSavedOrder相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getSavedOrder(): string[] {
  return readJsonPref<string[]>(CATEGORY_ORDER_KEY, [])
}

/**
 * 用途：执行buildCategoryList相关业务逻辑。
 * @param customCategories 调用方传入的customCategories参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function buildCategoryList(customCategories: string[]) {
  const list = PREDEFINED_CATEGORIES.slice()
  for (const item of customCategories) {
    if (item && !PREDEFINED_VALUES.has(item)) {
      list.push({ label: item, value: item })
    }
  }

  const order = getSavedOrder()
  if (order.length === 0) return list
  /**
   * 用途：执行orderIndex相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
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

/**
 * 用途：执行matchesQuery相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行filteredDocuments相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const filteredDocuments = computed(() => documents.value.filter((doc) => matchesQuery(doc)))
/**
 * 用途：执行documentCount相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const documentCount = computed(() => filteredDocuments.value.length)

/**
 * 用途：执行sortPinned相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function sortPinned(items: KnowledgeDocument[]) {
  return [...items].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1
    if (!a.is_pinned && b.is_pinned) return 1
    return 0
  })
}

/**
 * 用途：执行folderFilterParams相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderFilterParams() {
  if (activeFolderMode.value === 'folder' && activeFolderId.value) {
    /**
     * 用途：执行exists相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
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

/**
 * 用途：执行refreshCategories相关业务逻辑。
 * @param extra 调用方传入的extra参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshCategories(extra = extraCategories.value) {
  try {
    const res = await knowledgeApi.stats()
    const statsCats = res.data.categories ?? []
    const counts: Record<string, number> = {}
    for (const item of statsCats) {
      counts[item.category] = item.count
    }
    categoryCounts.value = counts
    /**
     * 用途：执行all相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const all = [...new Set([...statsCats.map((item) => item.category), ...extra])]
    allCategories.value = buildCategoryList(all)
    if (category.value && !allCategories.value.some((item) => item.value === category.value)) {
      category.value = ''
    }
  } catch {
    allCategories.value = buildCategoryList(extra)
  }
}

/**
 * 用途：执行loadFolders相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadFolders() {
  folderError.value = ''
  try {
    const res = await knowledgeApi.listFolders()
    folders.value = res.data.folders || []
    totalDocumentCount.value = res.data.total_count || 0
    unfiledCount.value = res.data.unfiled_count || 0
    /**
     * 用途：执行known相关业务逻辑。
     * 参数：无显式业务参数。
     * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
     */
    const known = new Set(folderOptions.value.map((item) => item.id))
    if (activeFolderMode.value === 'folder' && activeFolderId.value && !known.has(activeFolderId.value)) {
      selectFolder('all')
    }
  } catch (error) {
    folders.value = []
    folderError.value = getErrorMessage(error, '文件夹加载失败')
  }
}

/**
 * 用途：执行load相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function load() {
  loading.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const res = await knowledgeApi.list({
      ...folderFilterParams(),
      category: category.value || undefined,
    })
    documents.value = sortPinned(res.data.documents || [])
  } catch (error) {
    documents.value = []
    errorMessage.value = getErrorMessage(error, '文档加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * 用途：执行refreshAll相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshAll() {
  await loadFolders()
  await refreshCategories()
  await load()
}

/**
 * 用途：执行resetAndLoad相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function resetAndLoad() {
  void load()
}

/**
 * 用途：执行selectFolder相关业务逻辑。
 * @param mode 调用方传入的mode参数，用于驱动当前前端逻辑。
 * @param folderId 调用方传入的folderId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function selectFolder(mode: FolderMode, folderId: string | null = null) {
  activeFolderMode.value = mode
  activeFolderId.value = mode === 'folder' ? folderId : null
  resetAndLoad()
}

/**
 * 用途：执行toggleFolder相关业务逻辑。
 * @param folderId 调用方传入的folderId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleFolder(folderId: string) {
  const next = new Set(expandedFolderIds.value)
  if (next.has(folderId)) next.delete(folderId)
  else next.add(folderId)
  expandedFolderIds.value = next
}

/**
 * 用途：执行openCreateFolder相关业务逻辑。
 * @param parentId 调用方传入的parentId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openCreateFolder(parentId: string | null = null) {
  folderDialogMode.value = 'create'
  editingFolder.value = null
  folderFormName.value = ''
  folderFormParentId.value = parentId
  folderDialogOpen.value = true
}

/**
 * 用途：执行openEditFolder相关业务逻辑。
 * @param folder 调用方传入的folder参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openEditFolder(folder: KnowledgeFolder) {
  folderDialogMode.value = 'edit'
  editingFolder.value = folder
  folderFormName.value = folder.name
  folderFormParentId.value = folder.parent_id
  folderDialogOpen.value = true
}

/**
 * 用途：执行saveFolder相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行deleteFolder相关业务逻辑。
 * @param mode 调用方传入的mode参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
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

/**
 * 用途：执行openFilePicker相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openFilePicker() {
  if (!uploading.value) fileInput.value?.click()
}

/**
 * 用途：执行currentFolderIdForUpload相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function currentFolderIdForUpload(): string | null {
  return activeFolderMode.value === 'folder' ? activeFolderId.value : null
}

/**
 * 用途：执行uploadFiles相关业务逻辑。
 * @param fileList 调用方传入的fileList参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function uploadFiles(fileList: FileList | File[]) {
  const files = Array.from(fileList)
  if (!files.length || uploading.value) return

  uploading.value = true
  message.value = ''
  errorMessage.value = ''
  progressMessage.value = '正在上传文件...'
  progressValue.value = 0
  try {
    const result = await knowledgeApi.uploadStream(
      files,
      (event) => {
        progressValue.value = event.progress ?? progressValue.value
        progressMessage.value = event.filename ? `${event.filename}：${event.message || ''}` : event.message || progressMessage.value
        if (event.event_type === 'completed' || event.event_type === 'error') {
          void refreshAll()
        }
      },
      currentFolderIdForUpload(),
      category.value || undefined,
    )
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

/**
 * 用途：执行handleFileChange相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) await uploadFiles(input.files)
  input.value = ''
}

/**
 * 用途：执行openDocument相关业务逻辑。
 * @param documentId 调用方传入的documentId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openDocument(documentId: string) {
  void router.push(`/knowledge/${documentId}`)
}

/**
 * 用途：执行togglePin相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function togglePin(doc: KnowledgeDocument) {
  if (pinningId.value) return
  pinningId.value = doc.id
  message.value = ''
  errorMessage.value = ''
  try {
    const res = await knowledgeApi.pin(doc.id)
    documents.value = sortPinned(documents.value.map((item) => (item.id === doc.id ? { ...item, is_pinned: res.data.is_pinned } : item)))
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '置顶失败')
  } finally {
    pinningId.value = ''
  }
}

/**
 * 用途：执行deleteDocument相关业务逻辑。
 * @param doc 调用方传入的doc参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function deleteDocument(doc: KnowledgeDocument) {
  if (deletingId.value) return
  const filename = getDocumentTitle(doc)
  const confirmed = await confirmDialog({
    title: '删除文档',
    message: `确认删除「${filename}」？删除后会从知识库检索中移除。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!confirmed) return

  deletingId.value = doc.id
  message.value = ''
  errorMessage.value = ''
  try {
    await knowledgeApi.delete(doc.id)
    documents.value = documents.value.filter((item) => item.id !== doc.id)
    await refreshAll()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '删除文档失败，请稍后重试')
  } finally {
    deletingId.value = ''
  }
}

/**
 * 用途：执行createCategory相关业务逻辑。
 * @param name 调用方传入的name参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function createCategory(name: string) {
  if (!extraCategories.value.includes(name)) {
    extraCategories.value = [...extraCategories.value, name]
  }
}

onMounted(() => {
  void refreshAll()
})

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch(category, () => {
  resetAndLoad()
})

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
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
              <span class="truncate" data-i18n-skip>{{ row.folder.name }}</span>
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
                  <h3 class="truncate text-sm font-medium text-[var(--color-text)]" data-i18n-skip>{{ getDocumentTitle(doc) }}</h3>
                  <div class="flex shrink-0 items-center gap-1">
                    <button
                      class="rounded p-0.5 hover:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      :disabled="pinningId === doc.id"
                      :title="doc.is_pinned ? '取消置顶' : '置顶'"
                      @click.stop="togglePin(doc)"
                    >
                      <Pin :size="14" :class="doc.is_pinned ? 'fill-[var(--color-accent)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'" />
                    </button>
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
                <p class="mb-2 line-clamp-2 text-xs text-[var(--color-text-secondary)]" data-i18n-skip>{{ getDocumentPreview(doc) }}</p>
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="doc.folder_id" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Folder :size="10" />
                    <span data-i18n-skip>{{ folderName(doc.folder_id) }}</span>
                  </span>
                  <span v-if="doc.category" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Tag :size="10" />
                    {{ categoryLabel(doc.category) }}
                  </span>
                  <span class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ getDocumentTypeLabel(doc) }}</span>
                  <span v-for="tag in doc.tags || []" :key="tag" class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]" data-i18n-skip>{{ tag }}</span>
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
        <p class="mb-5 text-sm leading-relaxed text-[var(--color-text-secondary)]">{{ `删除「${deleteFolderTarget.name}」时，可以将其中文档移回未归档，或同时删除该文件夹内的文档。` }}</p>
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
