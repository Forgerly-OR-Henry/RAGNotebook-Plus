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
import { notesApi } from '../api/notes'
import type { Note, NoteFolder } from '../types/api'

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
  folder: NoteFolder
  depth: number
}

interface FolderOption {
  id: string
  name: string
  depth: number
}

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
const page = ref(1)
const category = ref('')
const searchQuery = ref('')
const loading = ref(false)
const hasMore = ref(false)
const importing = ref(false)
const actionError = ref('')
const importError = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const sentinelRef = ref<HTMLElement | null>(null)
const observer = ref<IntersectionObserver | null>(null)

const folders = ref<NoteFolder[]>([])
const folderError = ref('')
const totalNoteCount = ref(0)
const currentTotalCount = ref(0)
const unfiledCount = ref(0)
const activeFolderMode = ref<FolderMode>('all')
const activeFolderId = ref<string | null>(null)
const expandedFolderIds = ref<Set<string>>(new Set())
const folderDialogOpen = ref(false)
const folderDialogMode = ref<'create' | 'edit'>('create')
const folderFormName = ref('')
const folderFormParentId = ref<string | null>(null)
const editingFolder = ref<NoteFolder | null>(null)
const deleteFolderTarget = ref<NoteFolder | null>(null)
const movingFolder = ref(false)

const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const mindMapModalOpen = ref(false)
const deleteConfirmOpen = ref(false)
const categoryModalOpen = ref(false)
const folderMoveOpen = ref(false)
const folderMoveTargetId = ref<string | null>(null)
const moveDialogOpen = ref(false)
const leftScopeId = ref<string | null>(null)
const rightScopeId = ref<string | null>(null)
const leftNotes = ref<Note[]>([])
const rightNotes = ref<Note[]>([])
const leftSelectedIds = ref<Set<string>>(new Set())
const rightSelectedIds = ref<Set<string>>(new Set())
const moveBusy = ref(false)
const moveError = ref('')
const manageOpen = ref(false)
const customCategory = ref('')
const extraCategories = ref<string[]>([])
const allCategories = ref(PREDEFINED_CATEGORIES)
const categoryCounts = ref<Record<string, number>>({})
const longPressTimer = ref<number | undefined>()
const enteredViaLongPress = ref(false)
const pointerMoved = ref(false)
const pressStartPos = ref({ x: 0, y: 0 })

const folderNameById = computed(() => {
  const map = new Map<string, string>()
  const walk = (nodes: NoteFolder[]) => {
    for (const node of nodes) {
      map.set(node.id, node.name)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(folders.value)
  return map
})

const selectedCount = computed(() => selectedIds.value.size)
const mindMapNoteIds = computed(() => Array.from(selectedIds.value))
const leftMoveAllSelected = computed(() => leftSelectedIds.value.size === leftNotes.value.length && leftNotes.value.length > 0)
const rightMoveAllSelected = computed(() => rightSelectedIds.value.size === rightNotes.value.length && rightNotes.value.length > 0)
const moveSameScope = computed(() => leftScopeId.value === rightScopeId.value)
const moveScopeWarning = computed(() => (moveSameScope.value ? '左右文件夹相同，请选择不同文件夹后再移动。' : ''))
const canMoveLeftToRight = computed(() => leftSelectedIds.value.size > 0 && !moveSameScope.value)
const canMoveRightToLeft = computed(() => rightSelectedIds.value.size > 0 && !moveSameScope.value)

const folderOptions = computed<FolderOption[]>(() => flattenFolders(folders.value, false))
const visibleFolderRows = computed<FolderRow[]>(() => flattenFolders(folders.value, true))
const activeFolderTitle = computed(() => {
  if (activeFolderMode.value === 'unfiled') return '未归档'
  if (activeFolderMode.value === 'folder') return folderName(activeFolderId.value) || '文件夹'
  return '全部笔记'
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

function descendantIds(folder: NoteFolder): string[] {
  const ids: string[] = []
  for (const child of folder.children || []) {
    ids.push(child.id, ...descendantIds(child))
  }
  return ids
}

function categoryLabel(value: string | null | undefined) {
  return value ? CATEGORY_LABEL_MAP[value] || value : ''
}

function folderName(value: string | null | undefined) {
  if (!value) return ''
  return folderNameById.value.get(value) || folderOptions.value.find((item) => item.id === value)?.name || `文件夹（${value.slice(0, 6)}）`
}

function folderOptionLabel(item: FolderOption) {
  const prefix = '-- '.repeat(item.depth)
  const name = item.name || `文件夹（${item.id.slice(0, 6)}）`
  return `${prefix}${name}`
}

function formatDate(date: string | null | undefined) {
  if (!date) return ''
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function getApiErrorMessage(error: unknown, fallbackMessage: string) {
  const apiError = error as ApiError
  const detail = apiError.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message?: unknown }).message)
  }
  return apiError.response?.data?.message || apiError.message || fallbackMessage
}

function sortPinned(items: Note[]) {
  return [...items].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1
    if (!a.is_pinned && b.is_pinned) return 1
    return 0
  })
}

function scopeLabel(scopeId: string | null) {
  if (scopeId === null) return '未归档'
  return folderName(scopeId)
}

function normalizeScopeId(scopeId: string | null) {
  if (!scopeId) return null
  return folderOptions.value.some((item) => item.id === scopeId) ? scopeId : null
}

function parseScopeInput(scopeId: string | null | undefined) {
  if (!scopeId || scopeId === UNFILED_SCOPE_VALUE || scopeId === 'null' || scopeId === 'undefined') return null
  return normalizeScopeId(scopeId) ? scopeId : null
}

function isFolderScopeInput(scopeId: string | null | undefined) {
  return Boolean(scopeId && scopeId !== UNFILED_SCOPE_VALUE && scopeId !== 'null' && scopeId !== 'undefined')
}

function scopeSelectValue(scopeId: string | null) {
  return scopeId ?? UNFILED_SCOPE_VALUE
}

function getDefaultRightScopeId(leftScope: string | null) {
  const target = folderOptions.value.find((item) => item.id !== leftScope)
  return target?.id || null
}

async function loadNotesByScopeWithRecovery(scopeId: string | null) {
  const targetScope = normalizeScopeId(scopeId)
  if (scopeId && !targetScope) {
    return loadNotesByScope(null)
  }
  return loadNotesByScope(targetScope)
}

async function ensureFoldersLoadedForMoveDialog() {
  if (!folderOptions.value.length) {
    await refreshFolders()
  }
}

function normalizeMoveSelection(selected: Set<string>, notesOfSide: Note[]) {
  const availableIds = new Set(notesOfSide.map((note) => note.id))
  const validIds = [...selected].filter((noteId) => availableIds.has(noteId))
  return validIds
}

function setScopePairFromCurrentView() {
  const currentFolderScope = activeFolderMode.value === 'folder' ? normalizeScopeId(activeFolderId.value) : null
  const right = currentFolderScope || getDefaultRightScopeId(null)
  leftScopeId.value = null
  rightScopeId.value = normalizeScopeId(right) ? normalizeScopeId(right) : null
}

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

async function refreshFolders() {
  folderError.value = ''
  try {
    const res = await notesApi.listFolders()
    folders.value = res.data.folders || []
    totalNoteCount.value = res.data.total_count || 0
    unfiledCount.value = res.data.unfiled_count || 0
    const known = new Set(folderOptions.value.map((item) => item.id))
    if (activeFolderMode.value === 'folder' && activeFolderId.value && !known.has(activeFolderId.value)) {
      selectFolder('all')
    }
  } catch (error) {
    folderError.value = getApiErrorMessage(error, '文件夹加载失败')
  }
}

async function loadNotes(pageNum: number, reset = false) {
  if (loading.value) return
  loading.value = true
  actionError.value = ''
  try {
    const filters = folderFilterParams()
    const searchText = searchQuery.value.trim()
    if (searchText) {
      const res = await notesApi.search(searchText, 30, filters)
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

async function refreshCategories(extra = extraCategories.value) {
  try {
    const res = await notesApi.stats()
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

function resetAndLoad() {
  page.value = 1
  void loadNotes(1, true)
}

function selectFolder(mode: FolderMode, folderId: string | null = null) {
  activeFolderMode.value = mode
  activeFolderId.value = mode === 'folder' ? folderId : null
  exitSelectMode()
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

function openEditFolder(folder: NoteFolder) {
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

function openImportPicker() {
  if (!importing.value) fileInput.value?.click()
}

function newNote() {
  const query = activeFolderMode.value === 'folder' && activeFolderId.value ? { folder_id: activeFolderId.value } : {}
  void router.push({ path: '/notes/new', query })
}

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

async function togglePin(noteId: string) {
  try {
    await notesApi.pin(noteId)
    notes.value = sortPinned(notes.value.map((note) => (note.id === noteId ? { ...note, is_pinned: !note.is_pinned } : note)))
  } catch (error) {
    actionError.value = getApiErrorMessage(error, '置顶失败')
  }
}

function clearLongPress() {
  if (longPressTimer.value !== undefined) {
    window.clearTimeout(longPressTimer.value)
    longPressTimer.value = undefined
  }
}

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

function handlePointerMove(event: PointerEvent) {
  if (longPressTimer.value === undefined) return
  const dx = event.clientX - pressStartPos.value.x
  const dy = event.clientY - pressStartPos.value.y
  if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
    pointerMoved.value = true
    clearLongPress()
  }
}

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

function exitSelectMode() {
  selectMode.value = false
  selectedIds.value = new Set()
}

function openMindMapModal() {
  if (selectedIds.value.size === 0) return
  mindMapModalOpen.value = true
}

async function handleBatchPin() {
  const selectedNotes = notes.value.filter((note) => selectedIds.value.has(note.id))
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

async function closeMoveDialog() {
  moveDialogOpen.value = false
  moveError.value = ''
  leftSelectedIds.value = new Set()
  rightSelectedIds.value = new Set()
  leftNotes.value = []
  rightNotes.value = []
}

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

function toggleMoveAll(side: 'left' | 'right', checked: boolean) {
  if (side === 'left') {
    leftSelectedIds.value = checked ? new Set(leftNotes.value.map((note) => note.id)) : new Set()
    return
  }
  rightSelectedIds.value = checked ? new Set(rightNotes.value.map((note) => note.id)) : new Set()
}

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

watch([category, searchQuery], () => {
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
