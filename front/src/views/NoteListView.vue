<!--
模块职责：笔记列表页，负责搜索、筛选、文件夹、批量操作和快速新建入口。
主要协作：通过组合 API、状态、组件和路由来支撑当前页面或功能。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  CheckSquare,
  ArrowLeft,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  Pin,
  Plus,
  Search,
  Settings2,
  Square,
  Tag,
  Trash2,
  Upload,
} from '@lucide/vue'
import BatchActionBar from '../components/BatchActionBar.vue'
import CategoryManageDialog from '../components/CategoryManageDialog.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import MindMapModal from '../components/MindMapModal.vue'
import { readJsonPref } from '../api/localPrefs'
import { notesApi } from '../api/notes'
import { confirmDialog } from '../composables/useAppDialog'
import type { Note, NoteFolder } from '../types/api'

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
  folder: NoteFolder
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
}

/**
 * 接口：`FolderFlat` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface FolderFlat extends FolderOption, FolderRow {}

const router = useRouter()
const PREDEFINED_CATEGORIES = [
  { label: '全部', value: '' },
  { label: '工作', value: 'work' },
  { label: '学习', value: 'study' },
  { label: '生活', value: 'life' },
  { label: '技术', value: 'project' },
  { label: '其他', value: 'other' },
]
const CATEGORY_LABEL_MAP: Record<string, string> = {
  work: '工作',
  study: '学习',
  life: '生活',
  project: '技术',
  other: '其他',
}
const PREDEFINED_VALUES = new Set(['work', 'study', 'life', 'project', 'other'])
const CATEGORY_ORDER_KEY = 'note_category_order'
const UNFILED_SCOPE_VALUE = '__unfiled__'

const notes = ref<Note[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const page = ref(1)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const category = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const searchQuery = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const loading = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const hasMore = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const importing = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const deletingId = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const actionError = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const importError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const sentinelRef = ref<HTMLElement | null>(null)
const observer = ref<IntersectionObserver | null>(null)

const folders = ref<NoteFolder[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const folderError = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const totalNoteCount = ref(0)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const currentTotalCount = ref(0)
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
const editingFolder = ref<NoteFolder | null>(null)
const deleteFolderTarget = ref<NoteFolder | null>(null)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const movingFolder = ref(false)

// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const mindMapModalOpen = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const deleteConfirmOpen = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const categoryModalOpen = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const folderMoveOpen = ref(false)
const folderMoveTargetId = ref<string | null>(null)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const moveDialogOpen = ref(false)
const leftScopeId = ref<string | null>(null)
const rightScopeId = ref<string | null>(null)
const leftNotes = ref<Note[]>([])
const rightNotes = ref<Note[]>([])
const leftSelectedIds = ref<Set<string>>(new Set())
const rightSelectedIds = ref<Set<string>>(new Set())
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const moveBusy = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const moveError = ref('')
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const manageOpen = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const customCategory = ref('')
const extraCategories = ref<string[]>([])
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const allCategories = ref(PREDEFINED_CATEGORIES)
const categoryCounts = ref<Record<string, number>>({})
const longPressTimer = ref<number | undefined>()
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const enteredViaLongPress = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const pointerMoved = ref(false)
// 响应式状态：保存当前组件内部的临时 UI 或业务处理状态。
const pressStartPos = ref({ x: 0, y: 0 })

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
  const walk = (nodes: NoteFolder[]) => {
    for (const node of nodes) {
      map.set(node.id, node.name)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(folders.value)
  return map
})

/**
 * 用途：执行selectedCount相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const selectedCount = computed(() => selectedIds.value.size)
/**
 * 用途：执行mindMapNoteIds相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const mindMapNoteIds = computed(() => Array.from(selectedIds.value))
/**
 * 用途：执行leftMoveAllSelected相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const leftMoveAllSelected = computed(() => leftSelectedIds.value.size === leftNotes.value.length && leftNotes.value.length > 0)
/**
 * 用途：执行rightMoveAllSelected相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const rightMoveAllSelected = computed(() => rightSelectedIds.value.size === rightNotes.value.length && rightNotes.value.length > 0)
/**
 * 用途：执行moveSameScope相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const moveSameScope = computed(() => leftScopeId.value === rightScopeId.value)
/**
 * 用途：执行moveScopeWarning相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const moveScopeWarning = computed(() => (moveSameScope.value ? '左右文件夹相同，请选择不同文件夹后再移动。' : ''))
/**
 * 用途：执行canMoveLeftToRight相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const canMoveLeftToRight = computed(() => leftSelectedIds.value.size > 0 && !moveSameScope.value)
/**
 * 用途：执行canMoveRightToLeft相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
const canMoveRightToLeft = computed(() => rightSelectedIds.value.size > 0 && !moveSameScope.value)

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
  return '全部笔记'
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
 * 用途：执行flattenFolders相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @param visibleOnly 调用方传入的visibleOnly参数，用于驱动当前前端逻辑。
 * @param depth 调用方传入的depth参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function flattenFolders(items: NoteFolder[], visibleOnly: boolean, depth = 0): FolderFlat[] {
  const rows: FolderFlat[] = []
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
function descendantIds(folder: NoteFolder): string[] {
  const ids: string[] = []
  for (const child of folder.children || []) {
    ids.push(child.id, ...descendantIds(child))
  }
  return ids
}

/**
 * 用途：执行categoryLabel相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function categoryLabel(value: string | null | undefined) {
  return value ? CATEGORY_LABEL_MAP[value] || value : ''
}

/**
 * 用途：执行folderName相关业务逻辑。
 * @param value 调用方传入的value参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderName(value: string | null | undefined) {
  if (!value) return ''
  return folderNameById.value.get(value) || folderOptions.value.find((item) => item.id === value)?.name || `文件夹（${value.slice(0, 6)}）`
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
 * 用途：执行formatDate相关业务逻辑。
 * @param date 调用方传入的date参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function formatDate(date: string | null | undefined) {
  if (!date) return ''
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/**
 * 用途：执行getApiErrorMessage相关业务逻辑。
 * @param error 调用方传入的error参数，用于驱动当前前端逻辑。
 * @param fallbackMessage 调用方传入的fallbackMessage参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getApiErrorMessage(error: unknown, fallbackMessage: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallbackMessage
}

/**
 * 用途：执行sortPinned相关业务逻辑。
 * @param items 调用方传入的items参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function sortPinned(items: Note[]) {
  return [...items].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1
    if (!a.is_pinned && b.is_pinned) return 1
    return 0
  })
}

/**
 * 用途：执行scopeLabel相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function scopeLabel(scopeId: string | null) {
  if (scopeId === null) return '未归档'
  return folderName(scopeId)
}

/**
 * 用途：执行normalizeScopeId相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function normalizeScopeId(scopeId: string | null) {
  if (!scopeId) return null
  return folderOptions.value.some((item) => item.id === scopeId) ? scopeId : null
}

/**
 * 用途：执行parseScopeInput相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function parseScopeInput(scopeId: string | null | undefined) {
  if (!scopeId || scopeId === UNFILED_SCOPE_VALUE || scopeId === 'null' || scopeId === 'undefined') return null
  return normalizeScopeId(scopeId) ? scopeId : null
}

/**
 * 用途：执行isFolderScopeInput相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function isFolderScopeInput(scopeId: string | null | undefined) {
  return Boolean(scopeId && scopeId !== UNFILED_SCOPE_VALUE && scopeId !== 'null' && scopeId !== 'undefined')
}

/**
 * 用途：执行scopeSelectValue相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function scopeSelectValue(scopeId: string | null) {
  return scopeId ?? UNFILED_SCOPE_VALUE
}

/**
 * 用途：执行getDefaultRightScopeId相关业务逻辑。
 * @param leftScope 调用方传入的leftScope参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function getDefaultRightScopeId(leftScope: string | null) {
  /**
   * 用途：执行target相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const target = folderOptions.value.find((item) => item.id !== leftScope)
  return target?.id || null
}

/**
 * 用途：执行loadNotesByScopeWithRecovery相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadNotesByScopeWithRecovery(scopeId: string | null) {
  const targetScope = normalizeScopeId(scopeId)
  if (scopeId && !targetScope) {
    return loadNotesByScope(null)
  }
  return loadNotesByScope(targetScope)
}

/**
 * 用途：执行ensureFoldersLoadedForMoveDialog相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function ensureFoldersLoadedForMoveDialog() {
  if (!folderOptions.value.length) {
    await refreshFolders()
  }
}

/**
 * 用途：执行normalizeMoveSelection相关业务逻辑。
 * @param selected 调用方传入的selected参数，用于驱动当前前端逻辑。
 * @param notesOfSide 调用方传入的notesOfSide参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function normalizeMoveSelection(selected: Set<string>, notesOfSide: Note[]) {
  /**
   * 用途：执行availableIds相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const availableIds = new Set(notesOfSide.map((note) => note.id))
  /**
   * 用途：执行validIds相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const validIds = [...selected].filter((noteId) => availableIds.has(noteId))
  return validIds
}

/**
 * 用途：执行setScopePairFromCurrentView相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function setScopePairFromCurrentView() {
  const currentFolderScope = activeFolderMode.value === 'folder' ? normalizeScopeId(activeFolderId.value) : null
  const right = currentFolderScope || getDefaultRightScopeId(null)
  leftScopeId.value = null
  rightScopeId.value = normalizeScopeId(right) ? normalizeScopeId(right) : null
}

/**
 * 用途：执行folderFilterParams相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function folderFilterParams() {
  if (activeFolderMode.value === 'folder' && activeFolderId.value) {
    const safeActiveFolder = normalizeScopeId(activeFolderId.value)
    if (!safeActiveFolder) {
      activeFolderMode.value = 'all'
      activeFolderId.value = null
      return {}
    }
    return { folder_id: safeActiveFolder }
  }
  if (activeFolderMode.value === 'unfiled') return { unfiled: true }
  return {}
}

/**
 * 用途：执行refreshFolders相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshFolders() {
  folderError.value = ''
  try {
    const res = await notesApi.listFolders()
    folders.value = res.data.folders || []
    totalNoteCount.value = res.data.total_count || 0
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
    folderError.value = getApiErrorMessage(error, '文件夹加载失败')
  }
}

/**
 * 用途：执行loadNotes相关业务逻辑。
 * @param pageNum 调用方传入的pageNum参数，用于驱动当前前端逻辑。
 * @param reset 调用方传入的reset参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadNotes(pageNum: number, reset = false) {
  if (loading.value) return
  loading.value = true
  actionError.value = ''
  try {
    const filters = folderFilterParams()
    const searchText = searchQuery.value.trim()
    if (searchText) {
      const res = await notesApi.search(searchText, 30, filters)
      /**
       * 用途：执行items相关业务逻辑。
       * 参数：无显式业务参数。
       * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
       */
      const items = category.value ? res.data.notes.filter((note) => note.category === category.value) : res.data.notes
      notes.value = sortPinned(items)
      currentTotalCount.value = notes.value.length
      hasMore.value = false
      page.value = 1
      return
    }

    const res = await notesApi.list({
      page: pageNum,
      page_size: 20,
      category: category.value || undefined,
      ...filters,
    })
    const items = res.data.notes || []
    notes.value = reset ? sortPinned(items) : sortPinned([...notes.value, ...items])
    currentTotalCount.value = res.data.total_count
    hasMore.value = pageNum * 20 < res.data.total_count
    page.value = pageNum + 1
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '笔记加载失败')
  } finally {
    loading.value = false
  }
}

/**
 * 用途：执行loadNotesByScope相关业务逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function loadNotesByScope(scopeId: string | null) {
  const loaded: Note[] = []
  let pageNum = 1
  const pageSize = 100
  while (true) {
    const params = scopeId ? { folder_id: scopeId } : { unfiled: true }
    const res = await notesApi.list({
      page: pageNum,
      page_size: pageSize,
      ...params,
    })
    loaded.push(...(res.data.notes || []))
    if (loaded.length >= (res.data.total_count || 0)) break
    if (res.data.notes.length < pageSize) break
    pageNum += 1
  }
  return sortPinned(loaded)
}

/**
 * 用途：执行refreshCategories相关业务逻辑。
 * @param extra 调用方传入的extra参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function refreshCategories(extra = extraCategories.value) {
  try {
    const res = await notesApi.stats()
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
 * 用途：执行resetAndLoad相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function resetAndLoad() {
  page.value = 1
  void loadNotes(1, true)
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
  exitSelectMode()
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
function openEditFolder(folder: NoteFolder) {
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
  actionError.value = ''
  try {
    if (folderDialogMode.value === 'edit' && editingFolder.value) {
      await notesApi.updateFolder(editingFolder.value.id, {
        name,
        parent_id: folderFormParentId.value || null,
      })
    } else {
      await notesApi.createFolder({
        name,
        parent_id: folderFormParentId.value || null,
      })
    }
    folderDialogOpen.value = false
    await refreshFolders()
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '文件夹保存失败')
  } finally {
    movingFolder.value = false
  }
}

/**
 * 用途：执行deleteFolder相关业务逻辑。
 * @param mode 调用方传入的mode参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function deleteFolder(mode: 'unfile' | 'delete_notes') {
  const target = deleteFolderTarget.value
  if (!target) return
  try {
    await notesApi.deleteFolder(target.id, mode)
    const removed = new Set([target.id, ...descendantIds(target)])
    if (activeFolderId.value && removed.has(activeFolderId.value)) {
      activeFolderMode.value = 'all'
      activeFolderId.value = null
    }
    deleteFolderTarget.value = null
    await refreshFolders()
    await refreshCategories()
    await loadNotes(1, true)
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '文件夹删除失败')
  }
}

/**
 * 用途：执行openImportPicker相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openImportPicker() {
  if (!importing.value) fileInput.value?.click()
}

/**
 * 用途：执行newNote相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function newNote() {
  const query = activeFolderMode.value === 'folder' && activeFolderId.value ? { folder_id: activeFolderId.value } : {}
  void router.push({ path: '/notes/new', query })
}

/**
 * 用途：执行importSelectedFile相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function importSelectedFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importing.value = true
  importError.value = ''
  try {
    const folderId = activeFolderMode.value === 'folder' ? activeFolderId.value : null
    const res = await notesApi.importFile(file, category.value || undefined, folderId)
    await refreshCategories()
    await refreshFolders()
    await router.push(`/notes/${res.data.id}`)
  } catch (error) {
    importError.value = getApiErrorMessage(error, '导入失败，请确认文件格式和内容后重试')
  } finally {
    importing.value = false
    input.value = ''
  }
}

/**
 * 用途：执行togglePin相关业务逻辑。
 * @param noteId 调用方传入的noteId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function togglePin(noteId: string) {
  try {
    await notesApi.pin(noteId)
    notes.value = sortPinned(notes.value.map((note) => (note.id === noteId ? { ...note, is_pinned: !note.is_pinned } : note)))
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '置顶失败')
  }
}

/**
 * 用途：执行deleteNote相关业务逻辑。
 * @param note 调用方传入的note参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function deleteNote(note: Note) {
  if (deletingId.value) return
  const confirmed = await confirmDialog({
    title: '删除笔记',
    message: `确认删除「${note.title || '无标题'}」？删除后无法恢复。`,
    confirmText: '删除',
    variant: 'danger',
  })
  if (!confirmed) return

  deletingId.value = note.id
  actionError.value = ''
  try {
    await notesApi.delete(note.id)
    await refreshCategories()
    await refreshFolders()
    await loadNotes(1, true)
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '删除笔记失败')
  } finally {
    deletingId.value = ''
  }
}

/**
 * 用途：执行clearLongPress相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function clearLongPress() {
  if (longPressTimer.value !== undefined) {
    window.clearTimeout(longPressTimer.value)
    longPressTimer.value = undefined
  }
}

/**
 * 用途：执行handlePointerDown相关业务逻辑。
 * @param noteId 调用方传入的noteId参数，用于驱动当前前端逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handlePointerDown(noteId: string, event: PointerEvent) {
  pressStartPos.value = { x: event.clientX, y: event.clientY }
  enteredViaLongPress.value = false
  pointerMoved.value = false
  clearLongPress()
  longPressTimer.value = window.setTimeout(() => {
    longPressTimer.value = undefined
    if (!selectMode.value) {
      enteredViaLongPress.value = true
      selectMode.value = true
      selectedIds.value = new Set([noteId])
    }
  }, 500)
}

/**
 * 用途：执行handlePointerMove相关业务逻辑。
 * @param event 调用方传入的event参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handlePointerMove(event: PointerEvent) {
  if (longPressTimer.value === undefined) return
  const dx = event.clientX - pressStartPos.value.x
  const dy = event.clientY - pressStartPos.value.y
  if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
    pointerMoved.value = true
    clearLongPress()
  }
}

/**
 * 用途：执行toggleNoteSelection相关业务逻辑。
 * @param noteId 调用方传入的noteId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleNoteSelection(noteId: string) {
  const next = new Set(selectedIds.value)
  if (next.has(noteId)) {
    next.delete(noteId)
  } else {
    next.add(noteId)
  }
  selectedIds.value = next
  if (next.size === 0) selectMode.value = false
}

/**
 * 用途：执行handlePointerUp相关业务逻辑。
 * @param noteId 调用方传入的noteId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function handlePointerUp(noteId: string) {
  const timerWasSet = longPressTimer.value !== undefined
  const wasLongPress = enteredViaLongPress.value
  enteredViaLongPress.value = false
  clearLongPress()

  if (wasLongPress || pointerMoved.value) return
  if (selectMode.value) {
    toggleNoteSelection(noteId)
  } else if (timerWasSet) {
    void router.push(`/notes/${noteId}`)
  }
}

/**
 * 用途：执行exitSelectMode相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function exitSelectMode() {
  selectMode.value = false
  selectedIds.value = new Set()
}

/**
 * 用途：执行openMindMapModal相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function openMindMapModal() {
  if (selectedIds.value.size === 0) return
  mindMapModalOpen.value = true
}

/**
 * 用途：执行handleBatchPin相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleBatchPin() {
  /**
   * 用途：执行selectedNotes相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const selectedNotes = notes.value.filter((note) => selectedIds.value.has(note.id))
  /**
   * 用途：执行allPinned相关业务逻辑。
   * 参数：无显式业务参数。
   * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
   */
  const allPinned = selectedNotes.length > 0 && selectedNotes.every((note) => note.is_pinned)
  const nextPinned = !allPinned
  try {
    await notesApi.batchPin(Array.from(selectedIds.value), nextPinned)
    notes.value = sortPinned(notes.value.map((note) => (selectedIds.value.has(note.id) ? { ...note, is_pinned: nextPinned } : note)))
    exitSelectMode()
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '批量置顶失败')
  }
}

/**
 * 用途：执行handleBatchDelete相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleBatchDelete() {
  try {
    await notesApi.batchDelete(Array.from(selectedIds.value))
    exitSelectMode()
    await refreshCategories()
    await refreshFolders()
    await loadNotes(1, true)
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '批量删除失败')
  }
}

/**
 * 用途：执行handleBatchDownload相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleBatchDownload() {
  try {
    const blob = await notesApi.batchDownload(Array.from(selectedIds.value))
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `notes_${new Date().toISOString().slice(0, 10)}.zip`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
    exitSelectMode()
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '批量下载失败')
  }
}

/**
 * 用途：执行handleBatchCategory相关业务逻辑。
 * @param nextCategory 调用方传入的nextCategory参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleBatchCategory(nextCategory: string) {
  try {
    await notesApi.batchUpdateCategory(Array.from(selectedIds.value), nextCategory)
    categoryModalOpen.value = false
    customCategory.value = ''
    exitSelectMode()
    await refreshCategories()
    await loadNotes(1, true)
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '批量修改分类失败')
  }
}

/**
 * 用途：执行handleBatchFolder相关业务逻辑。
 * @param nextFolderId 调用方传入的nextFolderId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function handleBatchFolder(nextFolderId: string | null) {
  try {
    await notesApi.batchUpdateFolder(Array.from(selectedIds.value), nextFolderId)
    folderMoveOpen.value = false
    folderMoveTargetId.value = null
    exitSelectMode()
    await refreshFolders()
    await loadNotes(1, true)
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '批量移动失败')
  }
}

/**
 * 用途：执行openMoveDialog相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function openMoveDialog() {
  await ensureFoldersLoadedForMoveDialog()
  setScopePairFromCurrentView()
  leftSelectedIds.value = new Set()
  rightSelectedIds.value = new Set()
  moveError.value = ''
  leftNotes.value = []
  rightNotes.value = []
  moveDialogOpen.value = true
  moveBusy.value = false
  try {
    const [loadedLeft, loadedRight] = await Promise.all([
      loadNotesByScopeWithRecovery(leftScopeId.value),
      loadNotesByScopeWithRecovery(rightScopeId.value),
    ])
    leftNotes.value = loadedLeft
    rightNotes.value = loadedRight
  } catch (error) {
    moveError.value = getApiErrorMessage(error, '加载文件夹列表失败')
  }
}

/**
 * 用途：执行closeMoveDialog相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function closeMoveDialog() {
  moveDialogOpen.value = false
  moveError.value = ''
  leftSelectedIds.value = new Set()
  rightSelectedIds.value = new Set()
  leftNotes.value = []
  rightNotes.value = []
}

/**
 * 用途：执行toggleMoveSelection相关业务逻辑。
 * @param side 调用方传入的side参数，用于驱动当前前端逻辑。
 * @param noteId 调用方传入的noteId参数，用于驱动当前前端逻辑。
 * @param checked 调用方传入的checked参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleMoveSelection(side: 'left' | 'right', noteId: string, checked: boolean) {
  if (side === 'left') {
    const next = new Set(leftSelectedIds.value)
    if (checked) {
      next.add(noteId)
    } else {
      next.delete(noteId)
    }
    leftSelectedIds.value = next
    return
  }
  const next = new Set(rightSelectedIds.value)
  if (checked) {
    next.add(noteId)
  } else {
    next.delete(noteId)
  }
  rightSelectedIds.value = next
}

/**
 * 用途：执行toggleMoveAll相关业务逻辑。
 * @param side 调用方传入的side参数，用于驱动当前前端逻辑。
 * @param checked 调用方传入的checked参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function toggleMoveAll(side: 'left' | 'right', checked: boolean) {
  if (side === 'left') {
    leftSelectedIds.value = checked ? new Set(leftNotes.value.map((note) => note.id)) : new Set()
    return
  }
  rightSelectedIds.value = checked ? new Set(rightNotes.value.map((note) => note.id)) : new Set()
}

/**
 * 用途：执行updateMoveScope相关业务逻辑。
 * @param side 调用方传入的side参数，用于驱动当前前端逻辑。
 * @param scopeId 调用方传入的scopeId参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function updateMoveScope(side: 'left' | 'right', scopeId: string | null) {
  const normalized = parseScopeInput(scopeId)
  if (side === 'left') {
    if (leftScopeId.value !== normalized) {
      moveError.value = normalized === null && isFolderScopeInput(scopeId) ? '来源文件夹不存在，已自动回退到未归档' : ''
      leftScopeId.value = normalized
    }
    leftSelectedIds.value = new Set()
  } else {
    if (rightScopeId.value !== normalized) {
      moveError.value = normalized === null && isFolderScopeInput(scopeId) ? '目标文件夹不存在，已自动回退到未归档' : ''
      rightScopeId.value = normalized
    }
    rightSelectedIds.value = new Set()
  }
  try {
    if (side === 'left') {
      leftNotes.value = await loadNotesByScopeWithRecovery(leftScopeId.value)
    } else {
      rightNotes.value = await loadNotesByScopeWithRecovery(rightScopeId.value)
    }
  } catch (error) {
    moveError.value = getApiErrorMessage(error, '加载列表失败')
  }
}

/**
 * 用途：执行moveSelectedNotes相关业务逻辑。
 * @param source 调用方传入的source参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
async function moveSelectedNotes(source: 'left' | 'right') {
  if (moveBusy.value) return

  const sourceScope = source === 'left' ? leftScopeId : rightScopeId
  const targetScope = source === 'left' ? rightScopeId : leftScopeId
  const sourceNotes = source === 'left' ? leftNotes.value : rightNotes.value
  const sourceSelected = source === 'left' ? leftSelectedIds : rightSelectedIds

  const resolvedSourceScope = normalizeScopeId(sourceScope.value)
  const resolvedTargetScope = normalizeScopeId(targetScope.value)
  let scopeUpdated = false

  if (sourceScope.value !== resolvedSourceScope) {
    sourceScope.value = resolvedSourceScope
    scopeUpdated = true
    moveError.value = '来源文件夹不存在，已自动回退到未归档'
  }

  if (targetScope.value !== resolvedTargetScope) {
    targetScope.value = resolvedTargetScope
    scopeUpdated = true
    moveError.value = '目标文件夹不存在，已自动回退到未归档'
  }

  const normalizedSourceScope = sourceScope.value
  const normalizedTargetScope = resolvedTargetScope

  if (normalizedSourceScope === normalizedTargetScope) {
    return
  }

  const validSourceSelected = normalizeMoveSelection(sourceSelected.value, sourceNotes)
  if (sourceSelected.value.size > validSourceSelected.length) {
    sourceSelected.value = new Set(validSourceSelected)
    moveError.value = '部分笔记已变更，已自动过滤无效项'
  }

  if (sourceSelected.value.size === 0) {
    if (scopeUpdated) {
      leftNotes.value = await loadNotesByScopeWithRecovery(leftScopeId.value)
      rightNotes.value = await loadNotesByScopeWithRecovery(rightScopeId.value)
    }
    return
  }

  if (scopeUpdated) {
    leftNotes.value = await loadNotesByScopeWithRecovery(leftScopeId.value)
    rightNotes.value = await loadNotesByScopeWithRecovery(rightScopeId.value)
  }

  moveBusy.value = true
  try {
    await notesApi.batchUpdateFolder(Array.from(sourceSelected.value), normalizedTargetScope)
    if (source === 'left') leftSelectedIds.value = new Set()
    else rightSelectedIds.value = new Set()
    const [updatedLeft, updatedRight] = await Promise.all([
      loadNotesByScopeWithRecovery(leftScopeId.value),
      loadNotesByScopeWithRecovery(rightScopeId.value),
    ])
    leftNotes.value = updatedLeft
    rightNotes.value = updatedRight
    await refreshFolders()
    await refreshCategories()
    await loadNotes(1, true)
  } catch (error) {
    const message = getApiErrorMessage(error, '移动失败')
    if (message.includes('不存在')) {
      moveError.value = message
      await refreshFolders()
      leftScopeId.value = normalizeScopeId(leftScopeId.value)
      rightScopeId.value = normalizeScopeId(rightScopeId.value)
      if (rightScopeId.value === leftScopeId.value) rightScopeId.value = null
      leftNotes.value = await loadNotesByScopeWithRecovery(leftScopeId.value)
      rightNotes.value = await loadNotesByScopeWithRecovery(rightScopeId.value)
      return
    }
    moveError.value = message
  } finally {
    moveBusy.value = false
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
  observer.value = new IntersectionObserver(([entry]) => {
    if (entry?.isIntersecting && hasMore.value && !loading.value) {
      void loadNotes(page.value)
    }
  }, { threshold: 0.1 })
  if (sentinelRef.value) observer.value.observe(sentinelRef.value)
  void refreshFolders()
  void refreshCategories()
  void loadNotes(1, true)
})

onBeforeUnmount(() => {
  observer.value?.disconnect()
  clearLongPress()
})

// 状态监听：在关键输入变化后同步副作用或刷新页面数据。
watch([category, searchQuery], () => {
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
      accept=".md,.markdown,.txt,.doc,.docx,text/markdown,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      @change="importSelectedFile"
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
          <span class="truncate">全部笔记</span>
        </span>
        <span>{{ totalNoteCount }}</span>
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
            <span class="ml-2 shrink-0">{{ row.folder.note_count }}</span>
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
            {{ selectMode ? `已选择 ${selectedCount} 篇` : `${activeFolderTitle} · 共 ${currentTotalCount} 篇` }}
          </div>
          <div v-if="!selectMode" class="flex items-center gap-2">
            <button class="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--color-border)] px-3 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" :disabled="importing" @click="openImportPicker">
              <Upload :size="15" />
              {{ importing ? '导入中' : '导入' }}
            </button>
            <button
              class="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--color-border)] px-3 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
              type="button"
              @click="openMoveDialog"
            >
              <Folder :size="15" />
              移动
            </button>
            <button class="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--color-accent)] px-4 text-sm font-medium text-white hover:opacity-90" type="button" @click="newNote">
              <Plus :size="15" />
              新建笔记
            </button>
          </div>
          <button v-else class="rounded-md border border-[var(--color-border)] px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="exitSelectMode">取消</button>
        </div>

        <template v-if="!selectMode">
          <div class="mb-4 flex flex-wrap gap-3">
            <select v-model="activeFolderSelect" class="h-10 rounded-md border border-[var(--color-border)] bg-[var(--color-card)] px-3 text-xs text-[var(--color-text)] outline-none md:hidden">
              <option value="all">全部笔记</option>
              <option value="unfiled">未归档</option>
              <option v-for="item in folderOptions" :key="item.id" :value="`folder:${item.id}`">{{ folderOptionLabel(item) }}</option>
            </select>
            <form class="relative min-w-56 flex-1" @submit.prevent="resetAndLoad">
              <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-placeholder)]" />
              <input
                v-model="searchQuery"
                class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-2 pl-9 pr-4 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-placeholder)] focus:ring-2 focus:ring-[var(--color-accent)]"
                placeholder="搜索笔记"
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
        </template>

        <p v-if="importError" class="mt-3 text-sm text-[var(--color-danger)]">{{ importError }}</p>
        <p v-if="actionError" class="mt-3 text-sm text-[var(--color-danger)]">{{ actionError }}</p>
        <p v-if="selectMode && notes.length > 0" class="mt-3 text-xs text-[var(--color-text-tertiary)]">点击笔记可继续选择，长按笔记也可进入选择模式。</p>

        <BatchActionBar
          v-if="selectMode && selectedCount > 0"
          class="mt-3"
          :selected-count="selectedCount"
          @cancel="exitSelectMode"
          @delete="deleteConfirmOpen = true"
          @download="handleBatchDownload"
          @category="categoryModalOpen = true"
          @folder="folderMoveOpen = true"
          @mindmap="openMindMapModal"
          @pin="handleBatchPin"
        />
      </section>

      <section class="min-h-0 flex-1 overflow-y-auto pr-2 pt-4">
        <div v-if="notes.length === 0 && !loading" class="flex min-h-64 flex-col items-center justify-center rounded-md border border-dashed border-[var(--color-border)] bg-[var(--color-card)] p-8 text-center">
          <FileText :size="48" class="mb-3 text-[var(--color-text-tertiary)]" />
          <p class="mb-4 text-sm text-[var(--color-text-secondary)]">暂无笔记</p>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-2 text-sm text-white" type="button" @click="newNote">新建笔记</button>
        </div>

        <div v-else class="grid gap-3">
          <article
            v-for="note in notes"
            :key="note.id"
            class="cursor-pointer rounded-md border bg-[var(--color-card)] px-5 py-4 transition-colors"
            :class="selectedIds.has(note.id) ? 'border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]' : 'border-[var(--color-border)] hover:border-[var(--color-accent)]'"
            @pointerdown="handlePointerDown(note.id, $event)"
            @pointermove="handlePointerMove"
            @pointerup="handlePointerUp(note.id)"
            @pointerleave="clearLongPress"
          >
            <div class="flex items-start gap-3">
              <div v-if="selectMode" class="mt-0.5 shrink-0 text-[var(--color-accent)]">
                <CheckSquare v-if="selectedIds.has(note.id)" :size="18" />
                <Square v-else :size="18" class="text-[var(--color-text-tertiary)]" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="mb-1 flex items-start justify-between gap-3">
                  <h3 class="truncate text-sm font-medium text-[var(--color-text)]">{{ note.title || '无标题' }}</h3>
                  <div class="flex shrink-0 items-center gap-1">
                    <button
                      class="rounded p-0.5 hover:bg-[var(--color-bg-secondary)]"
                      type="button"
                      :title="note.is_pinned ? '取消置顶' : '置顶'"
                      @click.stop="togglePin(note.id)"
                      @pointerdown.stop
                      @pointerup.stop
                    >
                      <Pin :size="14" :class="note.is_pinned ? 'fill-[var(--color-accent)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'" />
                    </button>
                    <span class="text-xs text-[var(--color-text-tertiary)]">{{ formatDate(note.created_at) }}</span>
                    <button
                      class="rounded p-0.5 text-[var(--color-text-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-50"
                      type="button"
                      :disabled="deletingId === note.id"
                      title="删除笔记"
                      @click.stop="deleteNote(note)"
                      @pointerdown.stop
                      @pointerup.stop
                    >
                      <Trash2 :size="14" />
                    </button>
                  </div>
                </div>
                <p class="mb-2 line-clamp-2 text-xs text-[var(--color-text-secondary)]">{{ note.content?.slice(0, 200) }}</p>
                <div class="flex flex-wrap items-center gap-2">
                  <span v-if="note.folder_id" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Folder :size="10" />
                    {{ folderName(note.folder_id) }}
                  </span>
                  <span v-for="tag in note.tags || []" :key="tag" class="rounded-full bg-[var(--color-accent-bg)] px-2 py-0.5 text-xs text-[var(--color-accent)]">{{ tag }}</span>
                  <span v-if="note.category" class="inline-flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]">
                    <Tag :size="10" />
                    {{ categoryLabel(note.category) }}
                  </span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <div ref="sentinelRef" class="h-4" />
        <div v-if="loading" class="flex justify-center py-4">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]" />
        </div>
      </section>
    </div>

    <ConfirmDialog
      v-model:open="deleteConfirmOpen"
      title="删除笔记"
      :message="`确认删除选中的 ${selectedCount} 篇笔记？删除后无法恢复。`"
      variant="danger"
      confirm-text="删除"
      @confirm="handleBatchDelete"
    />

    <Teleport to="body">
      <div v-if="categoryModalOpen" class="fixed inset-0 z-50 bg-black/40" @click="categoryModalOpen = false" />
      <section v-if="categoryModalOpen" class="fixed left-1/2 top-1/2 z-50 w-[400px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
        <h3 class="mb-4 text-base font-medium text-[var(--color-text)]">修改分类</h3>
        <div class="mb-4 flex flex-wrap gap-2">
          <button
            v-for="item in allCategories.filter((entry) => entry.value !== '')"
            :key="item.value"
            class="rounded-md bg-[var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-accent-bg)] hover:text-[var(--color-accent)]"
            type="button"
            @click="handleBatchCategory(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="border-t border-[var(--color-border)] pt-4">
          <p class="mb-2 text-xs text-[var(--color-text-tertiary)]">自定义分类</p>
          <div class="flex gap-2">
            <input v-model="customCategory" class="flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-1.5 text-sm outline-none" placeholder="输入分类名称" />
            <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white disabled:opacity-40" type="button" :disabled="!customCategory.trim()" @click="handleBatchCategory(customCategory.trim())">确定</button>
          </div>
        </div>
      </section>
    </Teleport>

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
        <p class="mb-5 text-sm leading-relaxed text-[var(--color-text-secondary)]">删除「{{ deleteFolderTarget.name }}」时，可以将其中笔记移回未归档，或同时删除该文件夹内的笔记。</p>
        <div class="flex flex-wrap justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="deleteFolderTarget = null">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white" type="button" @click="deleteFolder('unfile')">移回未归档</button>
          <button class="rounded-md bg-red-500 px-4 py-1.5 text-sm text-white hover:bg-red-600" type="button" @click="deleteFolder('delete_notes')">同时删除笔记</button>
        </div>
      </section>
    </Teleport>

    <Teleport to="body">
      <div v-if="folderMoveOpen" class="fixed inset-0 z-50 bg-black/40" @click="folderMoveOpen = false" />
      <section v-if="folderMoveOpen" class="fixed left-1/2 top-1/2 z-50 w-[400px] max-w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
        <h3 class="mb-4 text-base font-medium text-[var(--color-text)]">移动到文件夹</h3>
        <select v-model="folderMoveTargetId" class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-sm outline-none">
          <option :value="null">未归档</option>
          <option v-for="item in folderOptions" :key="item.id" :value="item.id">{{ folderOptionLabel(item) }}</option>
        </select>
        <div class="mt-5 flex justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="folderMoveOpen = false">取消</button>
          <button class="rounded-md bg-[var(--color-accent)] px-4 py-1.5 text-sm text-white" type="button" @click="handleBatchFolder(folderMoveTargetId)">移动</button>
        </div>
      </section>
    </Teleport>

    <Teleport to="body">
      <div v-if="moveDialogOpen" class="fixed inset-0 z-50 bg-black/40" @click="closeMoveDialog" />
      <section v-if="moveDialogOpen" class="fixed left-1/2 top-1/2 z-50 w-[960px] max-w-[96vw] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-[var(--color-card)] p-6 shadow-xl">
        <h3 class="mb-4 text-base font-medium text-[var(--color-text)]">移动笔记</h3>

        <p v-if="moveError" class="mb-3 text-sm text-[var(--color-danger)]">{{ moveError }}</p>
        <p v-if="moveScopeWarning" class="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">{{ moveScopeWarning }}</p>

        <div class="grid gap-3 md:grid-cols-[1fr_auto_1fr]">
          <section>
            <div class="mb-2 flex items-center justify-between">
              <label class="text-xs text-[var(--color-text-secondary)]">左侧</label>
              <select
                class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2 py-1 text-xs"
                :value="scopeSelectValue(leftScopeId)"
                @change="updateMoveScope('left', ($event.target as HTMLSelectElement).value)"
              >
                <option :value="UNFILED_SCOPE_VALUE">未归档</option>
                <option v-for="item in folderOptions" :key="item.id" :value="item.id">{{ folderOptionLabel(item) }}</option>
              </select>
            </div>
            <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)]">
              <label class="flex items-center gap-2 border-b border-[var(--color-border)] px-2 py-2 text-xs text-[var(--color-text-secondary)]">
                <input type="checkbox" :checked="leftMoveAllSelected" @change="toggleMoveAll('left', ($event.target as HTMLInputElement).checked)" />
                全选
              </label>
              <div class="max-h-64 overflow-y-auto space-y-1 px-2 py-2">
                <p v-if="leftNotes.length === 0" class="py-4 text-center text-xs text-[var(--color-text-tertiary)]">{{ scopeLabel(leftScopeId) }}暂无内容</p>
                <label v-for="note in leftNotes" :key="note.id" class="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2 py-2 text-xs">
                  <input
                    type="checkbox"
                    :checked="leftSelectedIds.has(note.id)"
                    @change="toggleMoveSelection('left', note.id, ($event.target as HTMLInputElement).checked)"
                  />
                  <span class="truncate">{{ note.title || '无标题' }}</span>
                </label>
              </div>
            </div>
          </section>

          <div class="flex items-center justify-center gap-2 md:flex-col">
            <button
              class="inline-flex items-center justify-center rounded-md border border-[var(--color-border)] px-3 py-2 text-xs hover:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
              type="button"
              title="移到右侧"
              :disabled="moveBusy || !canMoveLeftToRight"
              @click="moveSelectedNotes('left')"
            >
              <ArrowRight :size="14" />
            </button>
            <button
              class="inline-flex items-center justify-center rounded-md border border-[var(--color-border)] px-3 py-2 text-xs hover:bg-[var(--color-bg-secondary)] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
              type="button"
              title="移到左侧"
              :disabled="moveBusy || !canMoveRightToLeft"
              @click="moveSelectedNotes('right')"
            >
              <ArrowLeft :size="14" />
            </button>
          </div>

          <section>
            <div class="mb-2 flex items-center justify-between">
              <label class="text-xs text-[var(--color-text-secondary)]">右侧</label>
              <select
                class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2 py-1 text-xs"
                :value="scopeSelectValue(rightScopeId)"
                @change="updateMoveScope('right', ($event.target as HTMLSelectElement).value)"
              >
                <option :value="UNFILED_SCOPE_VALUE">未归档</option>
                <option v-for="item in folderOptions" :key="item.id" :value="item.id">{{ folderOptionLabel(item) }}</option>
              </select>
            </div>
            <div class="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)]">
              <label class="flex items-center gap-2 border-b border-[var(--color-border)] px-2 py-2 text-xs text-[var(--color-text-secondary)]">
                <input type="checkbox" :checked="rightMoveAllSelected" @change="toggleMoveAll('right', ($event.target as HTMLInputElement).checked)" />
                全选
              </label>
              <div class="max-h-64 overflow-y-auto space-y-1 px-2 py-2">
                <p v-if="rightNotes.length === 0" class="py-4 text-center text-xs text-[var(--color-text-tertiary)]">{{ scopeLabel(rightScopeId) }}暂无内容</p>
                <label v-for="note in rightNotes" :key="note.id" class="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-2 py-2 text-xs">
                  <input
                    type="checkbox"
                    :checked="rightSelectedIds.has(note.id)"
                    @change="toggleMoveSelection('right', note.id, ($event.target as HTMLInputElement).checked)"
                  />
                  <span class="truncate">{{ note.title || '无标题' }}</span>
                </label>
              </div>
            </div>
          </section>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="rounded-md border border-[var(--color-border)] px-4 py-1.5 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]" type="button" @click="closeMoveDialog">关闭</button>
        </div>
      </section>
    </Teleport>

    <CategoryManageDialog
      v-model:open="manageOpen"
      :categories="allCategories.filter((entry) => entry.value !== '').map((entry) => ({ category: entry.value, count: categoryCounts[entry.value] ?? 0 }))"
      @refresh="refreshCategories"
      @create-category="createCategory"
    />

    <MindMapModal
      v-model:open="mindMapModalOpen"
      :note-ids="mindMapNoteIds"
    />
  </div>
</template>
